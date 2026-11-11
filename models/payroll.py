
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from models.employee import Employee


@dataclass
class Payroll:
    employee: Employee
    hra: Decimal = Decimal("0")
    other_allowances: Decimal = Decimal("0")
    pf_deduction: Decimal = Decimal("0")
    professional_tax: Decimal = Decimal("0")

    def __post_init__(self):
        self.hra = Decimal(str(self.hra))
        self.other_allowances = Decimal(str(self.other_allowances))
        self.pf_deduction = Decimal(str(self.pf_deduction))
        self.professional_tax = Decimal(str(self.professional_tax))

        values = [
            self.hra,
            self.other_allowances,
            self.pf_deduction,
            self.professional_tax
        ]

        if any(value < 0 for value in values):
            raise ValueError("Payroll amounts cannot be negative.")

        if self.pf_deduction + self.professional_tax > self.gross_salary:
            raise ValueError("Deductions cannot exceed gross salary.")

    @property
    def gross_salary(self):
        basic = Decimal(str(self.employee.basic_salary))
        return basic + self.hra + self.other_allowances

    @property
    def total_deductions(self):
        return self.pf_deduction + self.professional_tax

    @property
    def net_salary(self):
        return self.gross_salary - self.total_deductions

    def generate_payslip(self):
        print("\n" + "=" * 45)
        print("             EMPLOYEE PAYSLIP")
        print("=" * 45)

        print(f"Employee ID : {self.employee.emp_id}")
        print(f"Name        : {self.employee.name}")
        print(f"Department  : {self.employee.department}")

        print("-" * 45)
        print("EARNINGS")
        print(f"Basic Salary       : Rs. {self.employee.basic_salary:,.2f}")
        print(f"HRA                : Rs. {self.hra:,.2f}")
        print(f"Other Allowances   : Rs. {self.other_allowances:,.2f}")

        print("-" * 45)
        print(f"Gross Salary       : Rs. {self.gross_salary:,.2f}")

        print("\nDEDUCTIONS")
        print(f"PF                 : Rs. {self.pf_deduction:,.2f}")
        print(f"Professional Tax   : Rs. {self.professional_tax:,.2f}")
        print(f"Total Deductions   : Rs. {self.total_deductions:,.2f}")

        print("-" * 45)
        print(f"NET SALARY         : Rs. {self.net_salary:,.2f}")
        print("=" * 45)
