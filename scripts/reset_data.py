"""Reset the payroll data files.

Run from the project root:

    python scripts/reset_data.py --demo     # restore the sample dataset
    python scripts/reset_data.py --empty    # start with no records

The script only touches data/employees.csv, data/payroll.csv and the
data/DEMO_DATA.txt marker file used by the dashboard notice.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.employee import Employee
from models.payroll import Payroll

from storage import csv_manager
from storage.csv_manager import CSVManager


# ==============================
# SAMPLE DATASET
# ==============================

DEMO_EMPLOYEES = [
    ("EMP001", "Aditya Sharma", "Information Technology", "Senior Software Developer", "55000"),
    ("EMP002", "Priya Nair", "Human Resources", "HR Executive", "38000"),
    ("EMP003", "Rohan Mehta", "Finance", "Accounts Officer", "42000"),
    ("EMP004", "Sara Fernandes", "Marketing", "Marketing Lead", "50000"),
    ("EMP005", "Vikram Rao", "Operations", "Operations Manager", "60000"),
    ("EMP006", "Neha Kulkarni", "Information Technology", "Junior Developer", "32000"),
]

# (employee id, HRA, other allowances, PF, professional tax)
DEMO_PAYROLL = [
    ("EMP001", "22000", "8000", "6600", "200"),
    ("EMP002", "15200", "3000", "4560", "200"),
    ("EMP003", "16800", "4500", "5040", "200"),
    ("EMP004", "20000", "7000", "6000", "200"),
    ("EMP005", "24000", "9000", "7200", "200"),
]

DEMO_MARKER_TEXT = (
    "SAMPLE DEMONSTRATION DATA\n"
    "=========================\n\n"
    "employees.csv and payroll.csv currently contain the sample dataset that\n"
    "ships with the project. The names, salaries and payroll amounts are\n"
    "fictional and exist only to demonstrate the application.\n\n"
    "Restore this dataset:  python scripts/reset_data.py --demo\n"
    "Remove all records:    python scripts/reset_data.py --empty\n"
)


def marker_path():
    return csv_manager.DATA_DIR / "DEMO_DATA.txt"


def clear_files():
    """Delete and re-create both CSV files with their header row."""

    for path in (csv_manager.EMPLOYEE_FILE, csv_manager.PAYROLL_FILE):
        if path.exists():
            path.unlink()

    CSVManager.initialize_files()


def load_demo_data():
    for emp_id, name, department, designation, salary in DEMO_EMPLOYEES:
        CSVManager.save_employee(
            Employee(
                emp_id=emp_id,
                name=name,
                department=department,
                designation=designation,
                basic_salary=salary,
            )
        )

    employees = {employee.emp_id: employee for employee in CSVManager.load_employees()}

    for emp_id, hra, allowances, pf, tax in DEMO_PAYROLL:
        CSVManager.save_payroll(
            Payroll(
                employee=employees[emp_id],
                hra=hra,
                other_allowances=allowances,
                pf_deduction=pf,
                professional_tax=tax,
            )
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true",
                       help="restore the sample demonstration dataset")
    group.add_argument("--empty", action="store_true",
                       help="delete all records, keeping only the CSV headers")

    args = parser.parse_args()

    clear_files()
    marker_path().unlink(missing_ok=True)

    if args.demo:
        load_demo_data()
        marker_path().write_text(DEMO_MARKER_TEXT, encoding="utf-8")

        print("Sample dataset restored.")
        print(f"  employees: {len(CSVManager.load_employees())}")
        print(f"  payroll  : {len(CSVManager.load_payroll_records())}")
    else:
        print("All records removed. Both CSV files now contain only headers.")

    print(f"Data folder: {csv_manager.DATA_DIR}")


if __name__ == "__main__":
    main()
