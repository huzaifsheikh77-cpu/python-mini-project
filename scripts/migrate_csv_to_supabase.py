"""Migrate data/employees.csv and data/payroll.csv into Supabase PostgreSQL.

Run from the project root:

    python scripts/migrate_csv_to_supabase.py --dry-run   # inspect only
    python scripts/migrate_csv_to_supabase.py             # backup + import

Behaviour

* the CSV files are copied to data/backups/<UTC timestamp>/ first,
* every row is validated through the Employee / Payroll models,
* employees are inserted only when their emp_id does not exist yet,
* each payroll row carries a deterministic source_ref, so the script can be
  run again without creating duplicates,
* existing database rows are never updated or overwritten,
* a full log is written to logs/migration_<UTC timestamp>.log.

Exit codes: 0 = success, 1 = completed with rejected rows, 2 = configuration
problem (no DATABASE_URL, missing schema).
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from storage import csv_manager
from storage.database import StorageError, get_database_url
from storage.database_store import DatabaseStore
from storage.migration import backup_csv_files, format_summary, run_migration


def configure_logging(log_dir):
    log_dir = Path(log_dir or (PROJECT_ROOT / "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_file = log_dir / f"migration_{stamp}.log"

    logger = logging.getLogger("payroll.migration")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")
    )
    logger.addHandler(file_handler)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(console)

    return logger, log_file


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="validate and report without writing to the database")
    parser.add_argument("--no-backup", action="store_true",
                        help="skip copying the CSV files to data/backups/")
    parser.add_argument("--employees", default=None,
                        help="path to employees.csv (default: data/employees.csv)")
    parser.add_argument("--payroll", default=None,
                        help="path to payroll.csv (default: data/payroll.csv)")
    parser.add_argument("--log-dir", default=None,
                        help="directory for the migration log (default: logs/)")

    args = parser.parse_args(argv)

    if not get_database_url():
        print("DATABASE_URL is not set. Add your Supabase connection string to .env.")
        return 2

    logger, log_file = configure_logging(args.log_dir)

    employees_csv = Path(args.employees) if args.employees else csv_manager.EMPLOYEE_FILE
    payroll_csv = Path(args.payroll) if args.payroll else csv_manager.PAYROLL_FILE

    logger.info("Employee Payroll Management System - CSV migration")
    logger.info("Source employees: %s", employees_csv)
    logger.info("Source payroll  : %s", payroll_csv)
    logger.info("Dry run: %s", args.dry_run)

    if not args.no_backup:
        target, copied = backup_csv_files()
        logger.info("Backup %s: %s", target, ", ".join(copied) or "nothing to copy")
        print(f"Backup written to {target}")

    store = DatabaseStore()

    try:
        store.initialize_files()
    except StorageError as error:
        print(f"Database not ready: {error}")
        return 2

    try:
        summary = run_migration(
            store,
            employees_csv=employees_csv,
            payroll_csv=payroll_csv,
            logger=logger,
            dry_run=args.dry_run,
        )
        counts = store.counts()
    except StorageError as error:
        print(f"Migration failed: {error}")
        return 2

    print()
    print("Migration summary")
    print("-----------------")
    print(format_summary(summary))

    if args.dry_run:
        print(f"Database currently holds {counts['employees']} employees and "
              f"{counts['payroll_records']} payroll records (unchanged).")
    else:
        print(f"Database now holds {counts['employees']} employees and "
              f"{counts['payroll_records']} payroll records.")
    print(f"Log: {log_file}")

    if summary["discrepancies"]:
        print("\nRecalculation warnings (stored totals differ from the components):")
        for line in summary["discrepancies"]:
            print(f"  - {line}")

    if summary["notes"]:
        print("\nNotes:")
        for line in summary["notes"]:
            print(f"  - {line}")

    if summary["errors"]:
        print("\nRejected rows:")
        for line in summary["errors"]:
            print(f"  - {line}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
