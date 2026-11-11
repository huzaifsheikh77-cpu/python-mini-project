
from decimal import Decimal

import pytest

from models.employee import Employee
from models.payroll import Payroll


@pytest.fixture
def employee():
    return Employee(
        emp_id="EMP001",
        name="Huzaifa",
        department="Computer Science",
        designation="Software Developer",
        basic_salary=30000
    )


@pytest.fixture
def payroll(employee):
    return Payroll(
        employee=employee,
        hra=Decimal("8000"),
        other_allowances=Decimal("2000"),
        pf_deduction=Decimal("2000"),
        professional_tax=Decimal("200")
    )


def test_gross_salary_calculation(payroll):
    assert payroll.gross_salary == Decimal("40000")


def test_total_deductions_calculation(payroll):
    assert payroll.total_deductions == Decimal("2200")


def test_net_salary_calculation(payroll):
    assert payroll.net_salary == Decimal("37800")


def test_negative_allowance_rejected(employee):
    with pytest.raises(ValueError):
        Payroll(
            employee=employee,
            hra=Decimal("-1000")
        )


def test_deductions_cannot_exceed_gross_salary(employee):
    with pytest.raises(ValueError):
        Payroll(
            employee=employee,
            hra=Decimal("0"),
            other_allowances=Decimal("0"),
            pf_deduction=Decimal("30000"),
            professional_tax=Decimal("1000")
        )
