"""Safe, repeatable CSV -> PostgreSQL migration.

Rules implemented here:

* the existing CSV files are backed up before anything is read,
* every row is validated through the Employee / Payroll models,
* employees are inserted only when their ``emp_id`` is new,
* payroll rows carry a deterministic ``source_ref`` so re-running the
  migration never duplicates them,
* existing database rows are never overwritten,
* every skipped or invalid row is written to the migration log.
"""

import csv
import hashlib
import shutil
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from models.employee import Employee
from models.payroll import Payroll

from storage import csv_manager


PAYROLL_AMOUNT_FIELDS = (
    "hra",
    "other_allowances",
    "pf_deduction",
    "professional_tax",
)

PAYROLL_STORED_TOTALS = (
    ("gross_salary", "gross_salary"),
    ("total_deductions", "total_deductions"),
    ("net_salary", "net_salary"),
)


# ==============================
# BACKUP
# ==============================

def backup_csv_files(data_dir=None, backup_root=None):
    """Copy the CSV files into a timestamped folder before migration."""

    data_dir = Path(data_dir or csv_manager.DATA_DIR)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = Path(backup_root or (data_dir / "backups")) / stamp

    target.mkdir(parents=True, exist_ok=True)

    copied = []

    for name in ("employees.csv", "payroll.csv", "DEMO_DATA.txt"):
        source = data_dir / name

        if source.exists():
            shutil.copy2(source, target / name)
            copied.append(name)

    return target, copied


# ==============================
# CSV READING
# ==============================

def read_rows(path):
    """Read a CSV file into a list of dictionaries (empty when missing)."""

    path = Path(path)

    if not path.exists():
        return []

    with path.open("r", newline="", encoding="utf-8") as file:
        return [row for row in csv.DictReader(file) if any(row.values())]


def payroll_source_ref(row):
    """Deterministic identifier of one payroll CSV line."""

    parts = [
        str(row.get(field, "")).strip()
        for field in (
            "emp_id",
            "name",
            "department",
            "basic_salary",
            "hra",
            "other_allowances",
            "pf_deduction",
            "professional_tax",
        )
    ]

    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()

    return f"csv:{digest}"


# ==============================
# ROW BUILDERS
# ==============================

def build_employee(row):
    """Build a validated Employee from a CSV row (raises ValueError)."""

    return Employee(
        emp_id=row.get("emp_id", ""),
        name=row.get("name", ""),
        department=row.get("department", ""),
        designation=row.get("designation", ""),
        basic_salary=row.get("basic_salary", ""),
    )


def build_payroll(row, employees_by_id):
    """Build a Payroll from a CSV row plus any discrepancies found."""

    emp_id = str(row.get("emp_id", "")).strip()

    employee = employees_by_id.get(emp_id)
    notes = []

    if employee is None:
        # The employee row may have been deleted before the migration.
        # The payroll row is a historical snapshot, so it is still imported.
        employee = Employee(
            emp_id=emp_id,
            name=row.get("name", ""),
            department=row.get("department", ""),
            designation="Not recorded",
            basic_salary=row.get("basic_salary", ""),
        )
        notes.append(
            f"{emp_id}: no current employee record, snapshot imported with "
            "designation 'Not recorded'"
        )

    amounts = {}

    for field in PAYROLL_AMOUNT_FIELDS:
        raw = row.get(field, "")

        if raw is None or str(raw).strip() == "":
            amounts[field] = Decimal("0")
            continue

        try:
            amounts[field] = Decimal(str(raw).strip())
        except InvalidOperation:
            raise ValueError(f"{field} is not a number: {raw!r}")

    payroll = Payroll(employee=employee, **amounts)

    discrepancies = []

    for csv_field, attribute in PAYROLL_STORED_TOTALS:
        raw = row.get(csv_field, "")

        if raw is None or str(raw).strip() == "":
            continue

        try:
            stored = Decimal(str(raw).strip())
        except InvalidOperation:
            discrepancies.append(f"{emp_id}: {csv_field} is not a number ({raw!r})")
            continue

        calculated = getattr(payroll, attribute)

        if stored != calculated:
            discrepancies.append(
                f"{emp_id}: {csv_field} stored as {stored} but recalculated as {calculated}"
            )

    return payroll, discrepancies, notes


# ==============================
# MIGRATION
# ==============================

def run_migration(store, employees_csv=None, payroll_csv=None, logger=None, dry_run=False):
    """Import both CSV files into the store and return a summary."""

    def log(message):
        if logger is not None:
            logger.info(message)

    employees_csv = Path(employees_csv or csv_manager.EMPLOYEE_FILE)
    payroll_csv = Path(payroll_csv or csv_manager.PAYROLL_FILE)

    summary = {
        "dry_run": dry_run,
        "employees_total": 0,
        "employees_imported": 0,
        "employees_skipped": 0,
        "employees_invalid": 0,
        "payroll_total": 0,
        "payroll_imported": 0,
        "payroll_skipped": 0,
        "payroll_invalid": 0,
        "discrepancies": [],
        "notes": [],
        "errors": [],
    }

    employee_rows = read_rows(employees_csv)
    payroll_rows = read_rows(payroll_csv)

    summary["employees_total"] = len(employee_rows)
    summary["payroll_total"] = len(payroll_rows)

    existing_employees = {employee.emp_id for employee in store.load_employees()}
    valid_employees = {}

    log(f"Employees in CSV: {len(employee_rows)}")
    log(f"Employee IDs already in database: {len(existing_employees)}")

    for index, row in enumerate(employee_rows, start=2):
        emp_id = str(row.get("emp_id", "")).strip()

        try:
            employee = build_employee(row)
        except ValueError as error:
            summary["employees_invalid"] += 1
            summary["errors"].append(f"employees.csv line {index}: {error}")
            log(f"SKIP  employees.csv line {index} ({emp_id or 'no id'}): {error}")
            continue

        valid_employees[employee.emp_id] = employee

        if employee.emp_id in existing_employees:
            summary["employees_skipped"] += 1
            log(f"KEEP  {employee.emp_id}: already in database, not overwritten")
            continue

        if dry_run:
            summary["employees_imported"] += 1
            # Track ids so duplicates inside the same file are reported like
            # they would be by the unique constraint.
            existing_employees.add(employee.emp_id)
            log(f"WOULD INSERT employee {employee.emp_id} ({employee.name})")
            continue

        inserted = store.import_employee_row(employee)

        if inserted:
            summary["employees_imported"] += 1
            log(f"INSERT employee {employee.emp_id} ({employee.name})")
        else:
            summary["employees_skipped"] += 1
            log(f"KEEP  {employee.emp_id}: inserted concurrently, skipped")

    # Existing employees are needed as Payroll objects.
    by_id = {
        employee.emp_id: employee for employee in store.load_employees()
    }

    for emp_id, employee in valid_employees.items():
        by_id.setdefault(emp_id, employee)

    existing_refs = store.existing_source_refs() if not dry_run else set()

    log(f"Payroll rows in CSV: {len(payroll_rows)}")

    for index, row in enumerate(payroll_rows, start=2):
        emp_id = str(row.get("emp_id", "")).strip()

        try:
            payroll, discrepancies, notes = build_payroll(row, by_id)
        except ValueError as error:
            summary["payroll_invalid"] += 1
            summary["errors"].append(f"payroll.csv line {index}: {error}")
            log(f"SKIP  payroll.csv line {index} ({emp_id or 'no id'}): {error}")
            continue

        for note in notes:
            summary["notes"].append(note)
            log(f"NOTE  {note}")

        for discrepancy in discrepancies:
            summary["discrepancies"].append(discrepancy)
            log(f"WARN  {discrepancy}")

        source_ref = payroll_source_ref(row)

        if source_ref in existing_refs:
            summary["payroll_skipped"] += 1
            log(f"KEEP  payroll {emp_id} {source_ref}: already imported")
            continue

        if dry_run:
            summary["payroll_imported"] += 1
            existing_refs.add(source_ref)
            log(f"WOULD INSERT payroll {emp_id} net {payroll.net_salary}")
            continue

        inserted = store.import_payroll_row(payroll, source_ref)

        if inserted:
            summary["payroll_imported"] += 1
            existing_refs.add(source_ref)
            log(f"INSERT payroll {emp_id} net {payroll.net_salary}")
        else:
            summary["payroll_skipped"] += 1
            log(f"KEEP  payroll {emp_id} {source_ref}: conflict, skipped")

    return summary


def format_summary(summary):
    """Human readable multi-line summary of a migration run."""

    prefix = "DRY RUN - " if summary["dry_run"] else ""

    lines = [
        f"{prefix}Employees: {summary['employees_imported']} imported, "
        f"{summary['employees_skipped']} already present, "
        f"{summary['employees_invalid']} invalid "
        f"(of {summary['employees_total']} CSV rows)",
        f"{prefix}Payroll:   {summary['payroll_imported']} imported, "
        f"{summary['payroll_skipped']} already present, "
        f"{summary['payroll_invalid']} invalid "
        f"(of {summary['payroll_total']} CSV rows)",
    ]

    if summary["discrepancies"]:
        lines.append(f"Recalculation warnings: {len(summary['discrepancies'])}")

    if summary["notes"]:
        lines.append(f"Notes: {len(summary['notes'])}")

    if summary["errors"]:
        lines.append(f"Rejected rows: {len(summary['errors'])}")

    return "\n".join(lines)
