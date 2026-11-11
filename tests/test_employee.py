
import pytest

from models.employee import Employee


def test_employee_creation():
    employee = Employee(
        emp_id="EMP001",
        name="Huzaifa",
        department="Computer Science",
        designation="Software Developer",
        basic_salary=30000
    )

    assert employee.emp_id == "EMP001"
    assert employee.name == "Huzaifa"
    assert employee.department == "Computer Science"
    assert employee.basic_salary == 30000


def test_employee_rejects_empty_name():
    with pytest.raises(ValueError):
        Employee(
            emp_id="EMP002",
            name="",
            department="HR",
            designation="HR Executive",
            basic_salary=25000
        )


def test_employee_rejects_negative_salary():
    with pytest.raises(ValueError):
        Employee(
            emp_id="EMP003",
            name="Test User",
            department="IT",
            designation="Developer",
            basic_salary=-1000
        )
