
import csv
from decimal import Decimal

import pytest

from models.employee import Employee
from models.payroll import Payroll
from storage import csv_manager
from storage.csv_manager import CSVManager


@pytest.fixture
def temporary_csv_files(tmp_path, monkeypatch):
    employee_file = tmp_path / "employees.csv"
    payroll_file = tmp_path / "payroll.csv"

    monkeypatch.setattr(csv_manager, "DATA_DIR", tmp_path)
    monkeypatch.setattr(csv_manager, "EMPLOYEE_FILE", employee_file)
    monkeypatch.setattr(csv_manager, "PAYROLL_FILE", payroll_file)

    CSVManager.initialize_files()

    return employee_file, payroll_file


@pytest.fixture
def employee():
    return Employee(
        emp_id="TEST001",
        name="Test Employee",
        department="IT",
        designation="Developer",
        basic_salary=30000
    )


def test_csv_files_are_initialized(temporary_csv_files):
    employee_file, payroll_file = temporary_csv_files

    assert employee_file.exists()
    assert payroll_file.exists()

    with employee_file.open(encoding="utf-8") as file:
        assert next(csv.reader(file))[0] == "emp_id"

    with payroll_file.open(encoding="utf-8") as file:
        assert next(csv.reader(file))[0] == "emp_id"


def test_save_and_load_employee(temporary_csv_files, employee):
    CSVManager.save_employee(employee)

    employees = CSVManager.load_employees()

    assert len(employees) == 1
    assert employees[0].emp_id == "TEST001"
    assert employees[0].name == "Test Employee"
    assert employees[0].basic_salary == 30000


def test_duplicate_employee_id_rejected(temporary_csv_files, employee):
    CSVManager.save_employee(employee)

    with pytest.raises(ValueError, match="Employee ID already exists"):
        CSVManager.save_employee(employee)


def test_save_and_load_payroll(temporary_csv_files, employee):
    payroll = Payroll(
        employee=employee,
        hra=Decimal("8000"),
        other_allowances=Decimal("2000"),
        pf_deduction=Decimal("2000"),
        professional_tax=Decimal("200")
    )

    CSVManager.save_payroll(payroll)

    records = CSVManager.load_payroll_records()

    assert len(records) == 1
    assert records[0]["emp_id"] == "TEST001"
    assert float(records[0]["gross_salary"]) == 40000
    assert float(records[0]["net_salary"]) == 37800


def test_replace_employees(temporary_csv_files, employee):
    CSVManager.save_employee(employee)

    updated_employee = Employee(
        emp_id="TEST002",
        name="Updated Employee",
        department="HR",
        designation="Manager",
        basic_salary=45000
    )

    CSVManager.replace_employees([updated_employee])

    employees = CSVManager.load_employees()

    assert len(employees) == 1
    assert employees[0].emp_id == "TEST002"
    assert employees[0].name == "Updated Employee"
