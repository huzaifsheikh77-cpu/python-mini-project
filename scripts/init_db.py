"""Create or verify the payroll database schema.

Run from the project root:

    python scripts/init_db.py            # apply migrations (Supabase/PostgreSQL)
    python scripts/init_db.py --check    # only report what exists

The SQL files in migrations/ are applied in order and are idempotent, so the
script can be run repeatedly. For a local SQLite database the equivalent
SQLAlchemy schema is created instead.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import inspect

from storage import schema
from storage.database import StorageError, create_db_engine, get_database_url


MIGRATIONS_DIR = PROJECT_ROOT / "migrations"


def migration_files():
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def apply_migrations(engine):
    """Apply every SQL migration (PostgreSQL) or create the schema (SQLite)."""

    applied = []

    if engine.dialect.name == "sqlite":
        schema.metadata.create_all(engine)
        return ["sqlalchemy metadata (sqlite)"]

    for path in migration_files():
        sql = path.read_text(encoding="utf-8")

        with engine.begin() as connection:
            connection.exec_driver_sql(sql)

        applied.append(path.name)

    return applied


def table_report(engine):
    inspector = inspect(engine)
    names = inspector.get_table_names()

    report = []

    for table in ("employees", "payroll_records"):
        if table not in names:
            report.append(f"{table}: MISSING")
            continue

        columns = inspector.get_columns(table)
        indexes = [index["name"] for index in inspector.get_indexes(table)]

        report.append(
            f"{table}: {len(columns)} columns, indexes: "
            + (", ".join(sorted(indexes)) if indexes else "none")
        )

    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="report the schema without changing anything")

    args = parser.parse_args(argv)

    if not get_database_url():
        print("DATABASE_URL is not set. Add it to .env (see .env.example).")
        return 2

    try:
        engine = create_db_engine()
    except StorageError as error:
        print(f"Configuration error: {error}")
        return 2

    print(f"Target: {engine.url.render_as_string(hide_password=True)}")

    if not args.check:
        applied = apply_migrations(engine)

        for name in applied:
            print(f"applied: {name}")

    print("Schema:")
    for line in table_report(engine):
        print(f"  {line}")

    with engine.connect() as connection:
        for table in ("employees", "payroll_records"):
            try:
                count = connection.exec_driver_sql(
                    f"SELECT count(*) FROM {table}"
                ).scalar_one()
                print(f"  {table}: {count} rows")
            except Exception:
                print(f"  {table}: not available")

    engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
