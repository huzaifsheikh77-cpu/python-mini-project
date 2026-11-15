"""Database layer tests.

They run against PostgreSQL when PAYROLL_TEST_DATABASE_URL is set (the schema
from migrations/001_init_schema.sql is applied), otherwise against a
temporary SQLite file. Both paths exercise the same repository code.
"""

import csv
import os
from decimal import Decimal
from pathlib import Path

import pytest

from sqlalchemy import text

from models.employee import Employee
from models.payroll import Payroll

from storage import schema
from storage.backend import build_store, reset_store, set_store
from storage.database import StorageError, create_db_engine
from storage.database_store import DatabaseStore
from storage.migration import run_migration


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_SQL = (PROJECT_ROOT / "migrations" / "001_init_schema.sql").read_text(encoding="utf-8")

TEST_URL = os.environ.get("PAYROLL_TEST_DATABASE_URL", "").strip()

requires_postgres = pytest.mark.skipif(
    not TEST_URL, reason="PAYROLL_TEST_DATABASE_URL is not set"
)


# ==============================
# FIXTURES
# ==============================

@pytest.fixture
def db_target(tmp_path):
    if TEST_URL:
        return TEST_URL

    return f"sqlite:///{(tmp_path / 'payroll_test.db').as_posix()}"


def prepare_schema(engine):
    """Create a clean schema for one test."""

    if engine.dialect.name == "sqlite":
        schema.metadata.create_all(engine)
        return

    with engine.begin() as connection:
        connection.exec_driver_sql(SCHEMA_SQL)
        connection.exec_driver_sql(
            "TRUNCATE payroll_records, employees RESTART IDENTITY CASCADE"
        )


@pytest.fixture
def store(db_target):
    engine = create_db_engine(db_target)
    prepare_schema(engine)

    database_store = DatabaseStore(engine)
    set_store(database_store)

    try:
        yield database_store
    finally:
        reset_store()
        engine.dispose()


def make_employee(emp_id="EMP100", name="Database Test", salary="30000"):
    return Employee(
        emp_id=emp_id,
        name=name,
        department="Information Technology",
        designation="Developer",
        basic_salary=salary,
    )


def make_payroll(employee, hra="8000", allowances="2000", pf="2000", tax="200"):
    return Payroll(
        employee=employee,
        hra=hra,
        other_allowances=allowances,
        pf_deduction=pf,
        professional_tax=tax,
    )


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

    return path


# ==============================
# EMPLOYEES
# ==============================

def test_employee_create_and_retrieve(store):
    store.save_employee(make_employee())

    employees = store.load_employees()

    assert len(employees) == 1
    assert employees[0].emp_id == "EMP100"
    assert employees[0].name == "Database Test"
    assert employees[0].basic_salary == Decimal("30000")


def test_duplicate_employee_id_is_rejected(store):
    store.save_employee(make_employee())

    with pytest.raises(ValueError, match="Employee ID already exists"):
        store.save_employee(make_employee(name="Someone Else"))

    assert len(store.load_employees()) == 1


def test_employee_update_changes_fields(store):
    store.save_employee(make_employee())

    updated = store.update_employee(
        "EMP100",
        name="Renamed Person",
        department="Finance",
        designation="Analyst",
        basic_salary=Decimal("45500.50"),
    )

    assert updated is not None
    assert updated.name == "Renamed Person"
    assert updated.department == "Finance"
    assert updated.basic_salary == Decimal("45500.50")

    stored = store.load_employees()[0]
    assert stored.name == "Renamed Person"
    assert stored.basic_salary == Decimal("45500.50")


def test_employee_update_unknown_id_returns_none(store):
    assert store.update_employee("MISSING", name="Nobody") is None


def test_employee_delete_removes_record(store):
    store.save_employee(make_employee())

    assert store.delete_employee("EMP100") is True
    assert store.load_employees() == []
    assert store.delete_employee("EMP100") is False


# ==============================
# PAYROLL
# ==============================

def test_payroll_save_and_history(store):
    employee = make_employee()
    store.save_employee(employee)

    store.save_payroll(make_payroll(employee))

    records = store.load_payroll_records()

    assert len(records) == 1
    assert records[0]["emp_id"] == "EMP100"
    assert records[0]["gross_salary"] == Decimal("40000")
    assert records[0]["total_deductions"] == Decimal("2200")
    assert records[0]["net_salary"] == Decimal("37800")


def test_payroll_history_is_unchanged_after_employee_edit(store):
    employee = make_employee()
    store.save_employee(employee)
    store.save_payroll(make_payroll(employee))

    store.update_employee("EMP100", name="Renamed", basic_salary=Decimal("90000"))

    record = store.load_payroll_records()[0]

    assert record["name"] == "Database Test"
    assert record["basic_salary"] == Decimal("30000")
    assert record["net_salary"] == Decimal("37800")


def test_payroll_history_survives_employee_delete(store):
    employee = make_employee()
    store.save_employee(employee)
    store.save_payroll(make_payroll(employee))

    assert store.delete_employee("EMP100") is True

    records = store.load_payroll_records()

    assert len(records) == 1
    assert records[0]["name"] == "Database Test"
    assert records[0]["net_salary"] == Decimal("37800")

    with store.engine.connect() as connection:
        linked = connection.execute(
            text("SELECT employee_id FROM payroll_records")
        ).scalar_one()

    assert linked is None, "the foreign key must be cleared, not the snapshot"


def test_decimal_amounts_are_stored_exactly(store):
    employee = make_employee(salary="33333.33")
    store.save_employee(employee)

    store.save_payroll(
        make_payroll(
            employee,
            hra="1111.11",
            allowances="2222.22",
            pf="3333.33",
            tax="100.01",
        )
    )

    record = store.load_payroll_records()[0]

    assert record["basic_salary"] == Decimal("33333.33")
    assert record["hra"] == Decimal("1111.11")
    assert record["gross_salary"] == Decimal("36666.66")
    assert record["net_salary"] == Decimal("33233.32")

    # Decimal arithmetic, not float: 0.1 + 0.2 must be exactly 0.3.
    assert Decimal("36666.66") - Decimal("3433.34") == Decimal("33233.32")


def test_persistence_after_application_restart(store, db_target):
    employee = make_employee()
    store.save_employee(employee)
    store.save_payroll(make_payroll(employee))

    # Simulate a restart: drop the engine and connection pool completely.
    store.engine.dispose()

    restarted = DatabaseStore(create_db_engine(db_target))
    set_store(restarted)

    employees = restarted.load_employees()
    records = restarted.load_payroll_records()

    assert [item.emp_id for item in employees] == ["EMP100"]
    assert len(records) == 1
    assert records[0]["net_salary"] == Decimal("37800")

    restarted.engine.dispose()


def test_connection_error_raises_storage_error():
    unreachable = DatabaseStore(
        create_db_engine(
            "postgresql://postgres:not-a-real-password@127.0.0.1:59999/postgres"
            "?connect_timeout=2"
        )
    )

    with pytest.raises(StorageError):
        unreachable.load_employees()


# ==============================
# BACKEND SELECTION
# ==============================

def test_backend_selection_follows_environment(monkeypatch):
    monkeypatch.setenv("PAYROLL_STORAGE", "csv")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.com:5432/db")
    assert build_store().name == "csv"

    monkeypatch.setenv("PAYROLL_STORAGE", "database")
    assert build_store().name == "database"

    monkeypatch.delenv("PAYROLL_STORAGE")
    assert build_store().name == "database"

    monkeypatch.delenv("DATABASE_URL")
    assert build_store().name == "csv"


# ==============================
# CSV MIGRATION
# ==============================

EMPLOYEE_HEADER = ["emp_id", "name", "department", "designation", "basic_salary"]

PAYROLL_HEADER = [
    "emp_id", "name", "department", "basic_salary", "hra",
    "other_allowances", "pf_deduction", "professional_tax",
    "gross_salary", "total_deductions", "net_salary",
]

PAYROLL_ROW = [
    "EMP900", "Aarav Rao", "Information Technology", "40000",
    "10000", "2000", "4800", "200", "52000", "5000", "47000",
]


@pytest.fixture
def migration_files(tmp_path):
    employees_csv = write_csv(
        tmp_path / "employees.csv",
        EMPLOYEE_HEADER,
        [
            ["EMP900", "Aarav Rao", "Information Technology", "Developer", "40000"],
            ["EMP901", "Bela Shah", "Human Resources", "HR Executive", "30000"],
        ],
    )

    payroll_csv = write_csv(
        tmp_path / "payroll.csv",
        PAYROLL_HEADER,
        [PAYROLL_ROW, PAYROLL_ROW],  # the second line is an exact duplicate
    )

    return employees_csv, payroll_csv


def test_migration_imports_records_and_skips_duplicates(store, migration_files):
    employees_csv, payroll_csv = migration_files

    summary = run_migration(store, employees_csv, payroll_csv)

    assert summary["employees_imported"] == 2
    assert summary["payroll_imported"] == 1
    assert summary["payroll_skipped"] == 1
    assert len(store.load_employees()) == 2
    assert len(store.load_payroll_records()) == 1


def test_migration_is_repeatable(store, migration_files):
    employees_csv, payroll_csv = migration_files

    run_migration(store, employees_csv, payroll_csv)
    summary = run_migration(store, employees_csv, payroll_csv)

    assert summary["employees_imported"] == 0
    assert summary["employees_skipped"] == 2
    assert summary["payroll_imported"] == 0
    assert summary["payroll_skipped"] == 2
    assert len(store.load_employees()) == 2
    assert len(store.load_payroll_records()) == 1


def test_migration_never_overwrites_existing_employee(store, migration_files):
    employees_csv, payroll_csv = migration_files

    store.save_employee(
        Employee(
            emp_id="EMP900",
            name="Original Name",
            department="Finance",
            designation="Officer",
            basic_salary="41000",
        )
    )

    summary = run_migration(store, employees_csv, payroll_csv)

    assert summary["employees_skipped"] == 1
    assert summary["employees_imported"] == 1

    employees = {employee.emp_id: employee for employee in store.load_employees()}

    assert employees["EMP900"].name == "Original Name"
    assert employees["EMP900"].basic_salary == Decimal("41000")


def test_migration_reports_invalid_rows(store, tmp_path):
    employees_csv = write_csv(
        tmp_path / "employees.csv",
        EMPLOYEE_HEADER,
        [
            ["EMP902", "   ", "Finance", "Analyst", "45000"],
            ["EMP903", "Valid Person", "Finance", "Analyst", "45000"],
        ],
    )

    payroll_csv = write_csv(
        tmp_path / "payroll.csv",
        PAYROLL_HEADER,
        [["EMP903", "Valid Person", "Finance", "45000", "abc", "0", "0", "0", "0", "0", "0"]],
    )

    summary = run_migration(store, employees_csv, payroll_csv)

    assert summary["employees_imported"] == 1
    assert summary["employees_invalid"] == 1
    assert summary["payroll_invalid"] == 1
    assert len(summary["errors"]) == 2
    assert len(store.load_employees()) == 1


def test_migration_dry_run_writes_nothing(store, migration_files):
    employees_csv, payroll_csv = migration_files

    summary = run_migration(store, employees_csv, payroll_csv, dry_run=True)

    assert summary["employees_imported"] == 2
    assert summary["payroll_imported"] == 1
    assert store.load_employees() == []
    assert store.load_payroll_records() == []


# ==============================
# FLASK INTEGRATION
# ==============================

def test_flask_workflow_uses_database_store(store, tmp_path, monkeypatch):
    from analytics import charts as charts_module

    monkeypatch.setattr(charts_module, "CHART_DIR", tmp_path / "charts")

    import app as app_module

    app_module.app.config.update(TESTING=True, SECRET_KEY="database-test")

    client = app_module.app.test_client()

    created = client.post(
        "/employees/add",
        data={
            "emp_id": "EMP950",
            "name": "Web Person",
            "department": "Operations",
            "designation": "Coordinator",
            "basic_salary": "30000",
        },
    )

    assert created.status_code == 302
    assert len(store.load_employees()) == 1

    saved = client.post(
        "/payroll/save",
        data={
            "emp_id": "EMP950",
            "hra": "8000",
            "other_allowances": "2000",
            "pf_deduction": "2000",
            "professional_tax": "200",
        },
    )

    assert saved.status_code == 302
    assert len(store.load_payroll_records()) == 1

    history = client.get("/payroll")

    assert history.status_code == 200
    assert b"Web Person" in history.data
    assert b"37,800.00" in history.data
