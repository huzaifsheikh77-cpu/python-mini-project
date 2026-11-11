
import csv
from pathlib import Path

from models.employee import Employee
from models.payroll import Payroll


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

EMPLOYEE_FILE = DATA_DIR / "employees.csv"
PAYROLL_FILE = DATA_DIR / "payroll.csv"


class CSVManager:

    @staticmethod
    def initialize_files():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        if not EMPLOYEE_FILE.exists():
            with EMPLOYEE_FILE.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "emp_id",
                    "name",
                    "department",
                    "designation",
                    "basic_salary"
                ])

        if not PAYROLL_FILE.exists():
            with PAYROLL_FILE.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "emp_id",
                    "name",
                    "department",
                    "basic_salary",
                    "hra",
                    "other_allowances",
                    "pf_deduction",
                    "professional_tax",
                    "gross_salary",
                    "total_deductions",
                    "net_salary"
                ])

    @staticmethod
    def save_employee(employee):
        CSVManager.initialize_files()

        employees = CSVManager.load_employees()

        if any(emp.emp_id == employee.emp_id for emp in employees):
            raise ValueError("Employee ID already exists.")

        with EMPLOYEE_FILE.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            writer.writerow([
                employee.emp_id,
                employee.name,
                employee.department,
                employee.designation,
                employee.basic_salary
            ])

    @staticmethod
    def load_employees():
        CSVManager.initialize_files()

        employees = []

        with EMPLOYEE_FILE.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                employees.append(
                    Employee(
                        emp_id=row["emp_id"],
                        name=row["name"],
                        department=row["department"],
                        designation=row["designation"],
                        basic_salary=float(row["basic_salary"])
                    )
                )

        return employees

    @staticmethod
    def save_payroll(payroll):
        CSVManager.initialize_files()

        with PAYROLL_FILE.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            writer.writerow([
                payroll.employee.emp_id,
                payroll.employee.name,
                payroll.employee.department,
                payroll.employee.basic_salary,
                payroll.hra,
                payroll.other_allowances,
                payroll.pf_deduction,
                payroll.professional_tax,
                payroll.gross_salary,
                payroll.total_deductions,
                payroll.net_salary
            ])

    @staticmethod
    def load_payroll_records():
        CSVManager.initialize_files()

        with PAYROLL_FILE.open("r", newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    @staticmethod
    def replace_employees(employees):
        CSVManager.initialize_files()

        with EMPLOYEE_FILE.open(
            "w", newline="", encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "emp_id",
                "name",
                "department",
                "designation",
                "basic_salary"
            ])

            for employee in employees:
                writer.writerow([
                    employee.emp_id,
                    employee.name,
                    employee.department,
                    employee.designation,
                    employee.basic_salary
                ])
