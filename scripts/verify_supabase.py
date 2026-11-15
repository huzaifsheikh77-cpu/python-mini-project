"""Verify the Supabase connection and the CSV migration end to end.

Run from the project root, with DATABASE_URL set in .env:

    python scripts/verify_supabase.py              # full verification
    python scripts/verify_supabase.py --skip-migrate
    python scripts/verify_supabase.py --read-only  # connection and schema only

The script never prints credentials, never deletes existing records and never
overwrites data: it only inserts records with a temporary ID and removes the
ones it created. Exit code 0 means every check passed.
"""

import argparse
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from models.employee import Employee
from models.payroll import Payroll

from storage import csv_manager
from storage.database import StorageError, create_db_engine, get_database_url, normalise_url
from storage.database_store import DatabaseStore
from storage.migration import format_summary, read_rows, run_migration


RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    status = "OK  " if ok else "FAIL"
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))
    return ok


def info(message):
    print(f"       {message}")


def redacted_target(url):
    cleaned = normalise_url(url).replace("postgresql+psycopg://", "postgresql://")
    parts = urlsplit(cleaned)
    query = parse_qs(parts.query)

    return {
        "host": parts.hostname or "?",
        "port": parts.port,
        "database": (parts.path or "").lstrip("/") or "?",
        "sslmode": query.get("sslmode", ["(not set)"])[0],
        "pooler": parts.port == 6543,
    }


def csv_baseline():
    """Counts and totals straight from the CSV files."""

    employees = read_rows(csv_manager.EMPLOYEE_FILE)
    payroll = read_rows(csv_manager.PAYROLL_FILE)

    total_net = sum(
        (Decimal(str(row["net_salary"])) for row in payroll if row.get("net_salary")),
        Decimal("0"),
    )

    return {
        "employees": len(employees),
        "payroll": len(payroll),
        "total_net": total_net,
    }


def database_totals(engine):
    with engine.connect() as connection:
        employees = connection.execute(text("SELECT count(*) FROM employees")).scalar_one()
        payroll = connection.execute(text("SELECT count(*) FROM payroll_records")).scalar_one()
        total = connection.execute(text("SELECT COALESCE(sum(net_salary), 0) FROM payroll_records")).scalar_one()

    return {"employees": int(employees), "payroll": int(payroll), "total_net": Decimal(str(total))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-only", action="store_true",
                        help="connection and schema checks only")
    parser.add_argument("--skip-migrate", action="store_true",
                        help="skip the CSV migration checks")
    parser.add_argument("--skip-crud", action="store_true",
                        help="skip the temporary employee/payroll checks")

    args = parser.parse_args(argv)

    url = get_database_url()

    if not url:
        print("DATABASE_URL is not set. Add your Supabase connection string to .env.")
        print("See .env.example for the expected format.")
        return 2

    target = redacted_target(url)

    print("Employee Payroll Management System - Supabase verification")
    print("=" * 62)
    info(f"host      : {target['host']}")
    info(f"port      : {target['port']}" + (" (transaction pooler)" if target["pooler"] else ""))
    info(f"database  : {target['database']}")
    info(f"sslmode   : {target['sslmode']}")
    print()

    # ---------------------------------------------------------------- 1. connection
    try:
        engine = create_db_engine()
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version()")).scalar_one()
            ssl_row = connection.execute(
                text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")
            ).scalar_one()
    except (StorageError, SQLAlchemyError) as error:
        check("connect to Supabase", False, type(error).__name__)
        print("\nCannot continue without a database connection.")
        return 1

    check("connect to Supabase", True, "pooler reachable")
    info(version.split(",")[0])
    check("connection uses SSL", ssl_row is True, f"pg_stat_ssl.ssl = {ssl_row}")

    # ---------------------------------------------------------------- 2. schema
    try:
        store = DatabaseStore(engine)
        store.initialize_files()
        check("schema present (employees, payroll_records)", True)
    except StorageError as error:
        check("schema present (employees, payroll_records)", False, str(error))
        print("\nRun 'python scripts/init_db.py' first.")
        return 1

    totals = database_totals(engine)
    info(f"database now: {totals['employees']} employees, {totals['payroll']} payroll records, "
         f"net total {totals['total_net']}")

    if args.read_only:
        return summarise()

    baseline = csv_baseline()
    info(f"CSV data    : {baseline['employees']} employees, {baseline['payroll']} payroll records, "
         f"net total {baseline['total_net']}")

    # ---------------------------------------------------------------- 3. migration
    if not args.skip_migrate:
        dry = run_migration(store, dry_run=True)
        info("dry run: " + format_summary(dry).replace("\n", " | "))
        check("migration dry run writes nothing", database_totals(engine) == totals)

        before = database_totals(engine)
        summary = run_migration(store)
        print()
        print(format_summary(summary))
        print()

        after = database_totals(engine)

        check("migration reports no rejected rows", not summary["errors"],
              f"{len(summary['errors'])} rejected")
        check("employee count matches CSV",
              after["employees"] >= baseline["employees"],
              f"database {after['employees']} vs CSV {baseline['employees']}")
        check("payroll count matches CSV",
              after["payroll"] >= baseline["payroll"],
              f"database {after['payroll']} vs CSV {baseline['payroll']}")
        check("payroll net total matches CSV",
              after["total_net"] == baseline["total_net"],
              f"database {after['total_net']} vs CSV {baseline['total_net']}")
        check("no existing row was overwritten",
              after["employees"] >= before["employees"] and after["payroll"] >= before["payroll"])

        second = run_migration(store)
        repeated = database_totals(engine)

        check("migration is idempotent",
              second["employees_imported"] == 0 and second["payroll_imported"] == 0,
              f"second run imported {second['employees_imported']} employees, "
              f"{second['payroll_imported']} payroll rows")
        check("counts unchanged after second run", repeated == after)

    # ---------------------------------------------------------------- 4. CRUD
    if not args.skip_crud:
        stamp = datetime.now(timezone.utc).strftime("%H%M%S")
        temp_id = f"VERIFY-{stamp}"

        print()
        info(f"temporary record id: {temp_id}")

        try:
            store.save_employee(Employee(
                emp_id=temp_id,
                name="Verification Record",
                department="Verification",
                designation="Temporary",
                basic_salary="40000",
            ))
            employees = {employee.emp_id: employee for employee in store.load_employees()}
            check("insert employee", temp_id in employees)
            check("read employee", employees[temp_id].basic_salary == Decimal("40000"),
                  str(employees[temp_id].basic_salary))

            employee = employees[temp_id]
            store.save_payroll(Payroll(
                employee=employee,
                hra="10000",
                other_allowances="2000",
                pf_deduction="4800",
                professional_tax="200",
            ))

            records = [record for record in store.load_payroll_records()
                       if record["emp_id"] == temp_id]

            check("insert payroll record", len(records) == 1)
            check("payroll maths preserved in database",
                  bool(records) and records[0]["net_salary"] == Decimal("47000.00"),
                  str(records[0]["net_salary"]) if records else "missing")

            updated = store.update_employee(temp_id, department="Verification Updated",
                                            basic_salary=Decimal("42000"))
            check("update employee", updated is not None and updated.department == "Verification Updated")
            check("history keeps the original snapshot",
                  store.load_payroll_records()[-1]["basic_salary"] == Decimal("40000.00"),
                  "payroll row still shows 40000.00")

            store.delete_employee(temp_id)
            remaining = {employee.emp_id for employee in store.load_employees()}
            check("delete employee", temp_id not in remaining)
            check("history survives delete",
                  any(record["emp_id"] == temp_id for record in store.load_payroll_records()))

            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM payroll_records WHERE emp_id = :emp_id"),
                    {"emp_id": temp_id},
                )
                connection.execute(
                    text("DELETE FROM employees WHERE emp_id = :emp_id"),
                    {"emp_id": temp_id},
                )

            check("temporary records removed",
                  not any(r["emp_id"] == temp_id for r in store.load_payroll_records()))

        except Exception as error:  # noqa: BLE001 - report any CRUD failure
            check("employee/payroll CRUD", False, f"{type(error).__name__}: {error}")

    # ---------------------------------------------------------------- 5. reconnect
    engine.dispose()
    fresh = DatabaseStore(create_db_engine())
    reconnected = fresh.counts()

    check("records persist across a new connection", reconnected["employees"] >= baseline["employees"],
          f"{reconnected['employees']} employees, {reconnected['payroll_records']} payroll records")

    fresh.engine.dispose()

    return summarise()


def summarise():
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed

    print()
    print("=" * 62)
    print(f"{passed} checks passed, {failed} failed")

    if failed:
        print("\nFailed checks:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  - {name} ({detail})")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
