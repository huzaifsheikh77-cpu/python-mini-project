
from dataclasses import dataclass


@dataclass
class Employee:
    emp_id: str
    name: str
    department: str
    designation: str
    basic_salary: float

    def __post_init__(self):
        self.emp_id = self.emp_id.strip()
        self.name = self.name.strip()
        self.department = self.department.strip()
        self.designation = self.designation.strip()

        if not self.emp_id:
            raise ValueError("Employee ID cannot be empty.")

        if not self.name:
            raise ValueError("Employee name cannot be empty.")

        if not self.department:
            raise ValueError("Department cannot be empty.")

        if not self.designation:
            raise ValueError("Designation cannot be empty.")

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
