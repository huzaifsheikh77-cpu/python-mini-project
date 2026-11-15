
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Employee:
    emp_id: str
    name: str
    department: str
    designation: str
    basic_salary: Decimal

    def __post_init__(self):
        self.emp_id = str(self.emp_id).strip()
        self.name = str(self.name).strip()
        self.department = str(self.department).strip()
        self.designation = str(self.designation).strip()

        # Money is converted to Decimal immediately so that later salary
        # calculations never suffer from floating point rounding errors.
        self.basic_salary = Decimal(str(self.basic_salary))

        if not self.emp_id:
            raise ValueError("Employee ID cannot be empty.")

        if not self.name:
            raise ValueError("Employee name cannot be empty.")

        if not self.department:
            raise ValueError("Department cannot be empty.")

        if not self.designation:
            raise ValueError("Designation cannot be empty.")

        if not self.basic_salary.is_finite():
            raise ValueError("Basic salary must be a finite number.")

        if self.basic_salary <= 0:
            raise ValueError("Basic salary must be positive.")

    def display_details(self):
        print("\n========== EMPLOYEE DETAILS ==========")
        print(f"Employee ID : {self.emp_id}")
        print(f"Name        : {self.name}")
        print(f"Department  : {self.department}")
        print(f"Designation : {self.designation}")
        print(f"Basic Salary: Rs. {self.basic_salary:,.2f}")
        print("======================================")
