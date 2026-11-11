
from decimal import Decimal

from models.employee import Employee
from models.payroll import Payroll
from storage.csv_manager import CSVManager


# Load existing employee
employees = CSVManager.load_employees()

employee = next(
    (emp for emp in employees if emp.emp_id == "EMP001"),
    None
)

if employee is None:
    print("Employee not found.")
else:
    # Calculate payroll
    payroll = Payroll(
        employee=employee,
        hra=Decimal("8000"),
        other_allowances=Decimal("2000"),
        pf_deduction=Decimal("2000"),
        professional_tax=Decimal("200")
    )

    # Generate payslip
    payroll.generate_payslip()

    # Save payroll record
    CSVManager.save_payroll(payroll)

    print("\nPayroll record saved successfully!")
