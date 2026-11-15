"""Export the current database contents back to CSV files.

Run from the project root:

    python scripts/export_db_to_csv.py                 # data/exports/<timestamp>/
    python scripts/export_db_to_csv.py --out my_folder

The exported files use exactly the same columns as data/employees.csv and
data/payroll.csv, so they can be re-imported later.
"""

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from storage import csv_manager
from storage.backend import get_store
from storage.database import StorageError


EMPLOYEE_COLUMNS = ["emp_id", "name", "department", "designation", "basic_salary"]

PAYROLL_COLUMNS = [
    "emp_id",
    "name",
    "department",
    "basic_salary",
    "hra",
    "other_allowances",
    "pf_deduction",
    "professional_tax",
    "gross_salary",
    "total_deductions",
    "net_salary",
]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None,
                        help="output folder (default: data/exports/<UTC timestamp>)")

    args = parser.parse_args(argv)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = Path(args.out) if args.out else (csv_manager.DATA_DIR / "exports" / stamp)

    target.mkdir(parents=True, exist_ok=True)

    store = get_store()

    try:
        employees = store.load_employees()
        records = store.load_payroll_records()
    except StorageError as error:
        print(f"Export failed: {error}")
        return 2

    employees_path = target / "employees.csv"

    with employees_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(EMPLOYEE_COLUMNS)

        for employee in employees:
            writer.writerow([
                employee.emp_id,
                employee.name,
                employee.department,
                employee.designation,
                employee.basic_salary,
            ])

    payroll_path = target / "payroll.csv"

    with payroll_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(PAYROLL_COLUMNS)

        for record in records:
            writer.writerow([record[column] for column in PAYROLL_COLUMNS])

    print(f"Exported {len(employees)} employees -> {employees_path}")
    print(f"Exported {len(records)} payroll records -> {payroll_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
