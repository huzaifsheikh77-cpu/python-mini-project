
from decimal import Decimal, InvalidOperation

from models.employee import Employee
from models.payroll import Payroll

from storage.backend import get_store, init_storage
from services.employee_service import EmployeeService

from analytics.salary_analysis import SalaryAnalysis
from analytics.charts import PayrollCharts


# ==============================
# INPUT VALIDATION
# ==============================

def get_decimal_input(message, allow_zero=True):
    while True:
        try:
            value = Decimal(input(message).strip())

            if not value.is_finite():
                print("Please enter a finite number.")
                continue

            if value < 0 or (not allow_zero and value == 0):
                print("Invalid amount. Try again.")
                continue

            return value

        except InvalidOperation:
            print("Please enter a valid number.")


# ==============================
# EMPLOYEE MANAGEMENT
# ==============================

def add_employee():
    print("\n--- ADD NEW EMPLOYEE ---")

    try:
        employee = Employee(
            emp_id=input("Employee ID: "),
            name=input("Employee Name: "),
            department=input("Department: "),
            designation=input("Designation: "),
            basic_salary=float(
                get_decimal_input(
                    "Basic Salary: ",
                    allow_zero=False
                )
            )
        )

        EmployeeService.add_employee(employee)
        print("\nEmployee added successfully!")

    except ValueError as error:
        print(f"\nError: {error}")


def view_employees():
    print("\n--- ALL EMPLOYEES ---")

    employees = EmployeeService.get_all_employees()

    if not employees:
        print("No employees found.")
        return

    for employee in employees:
        employee.display_details()


def search_employee():
    print("\n--- SEARCH EMPLOYEE ---")

    emp_id = input("Enter Employee ID: ")

    employee = EmployeeService.search_employee(emp_id)

    if employee:
        employee.display_details()
    else:
        print("Employee not found.")


def update_employee():
    print("\n--- UPDATE EMPLOYEE ---")

    emp_id = input("Enter Employee ID: ")

    employee = EmployeeService.search_employee(emp_id)

    if not employee:
        print("Employee not found.")
        return

    print("Leave a field blank to keep its current value.")

    name = input(
        f"Name [{employee.name}]: "
    ).strip() or None

    department = input(
        f"Department [{employee.department}]: "
    ).strip() or None

    designation = input(
        f"Designation [{employee.designation}]: "
    ).strip() or None

    salary_input = input(
        f"Basic Salary [{employee.basic_salary}]: "
    ).strip()

    salary = None

    if salary_input:
        try:
            salary_value = Decimal(salary_input)

            if not salary_value.is_finite() or salary_value <= 0:
                print("Salary must be a positive finite number.")
                return

            salary = float(salary_value)

        except InvalidOperation:
            print("Invalid salary.")
            return

    try:
        updated = EmployeeService.update_employee(
            emp_id,
            name,
            department,
            designation,
            salary
        )

        if updated:
            print("Employee updated successfully!")
            updated.display_details()

    except ValueError as error:
        print("Error:", error)


def delete_employee():
    print("\n--- DELETE EMPLOYEE ---")

    emp_id = input("Enter Employee ID: ")

    employee = EmployeeService.search_employee(emp_id)

    if not employee:
        print("Employee not found.")
        return

    employee.display_details()

    confirmation = input(
        "Are you sure you want to delete this employee? (yes/no): "
    ).strip().lower()

    if confirmation == "yes":
        EmployeeService.delete_employee(emp_id)
        print("Employee deleted successfully.")
    else:
        print("Deletion cancelled.")


# ==============================
# PAYROLL MANAGEMENT
# ==============================

def process_payroll():
    print("\n--- PROCESS EMPLOYEE PAYROLL ---")

    emp_id = input("Enter Employee ID: ")

    employee = EmployeeService.search_employee(emp_id)

    if not employee:
        print("Employee not found.")
        return

    print(f"\nProcessing salary for {employee.name}")

    hra = get_decimal_input("Enter HRA: ")
    allowances = get_decimal_input("Other Allowances: ")
    pf = get_decimal_input("PF Deduction: ")
    tax = get_decimal_input("Professional Tax: ")

    try:
        payroll = Payroll(
            employee=employee,
            hra=hra,
            other_allowances=allowances,
            pf_deduction=pf,
            professional_tax=tax
        )

        payroll.generate_payslip()

        confirmation = input(
            "\nSave this payroll record? (yes/no): "
        ).strip().lower()

        if confirmation == "yes":
            get_store().save_payroll(payroll)
            print("Payroll record saved successfully.")
        else:
            print("Payroll record not saved.")

    except ValueError as error:
        print("Payroll error:", error)


def view_payroll_records():
    print("\n========== PAYROLL HISTORY ==========")

    records = get_store().load_payroll_records()

    print(f"Total records found: {len(records)}")

    if not records:
        print("No payroll records available.")
        return

    for index, record in enumerate(records, start=1):
        print(f"\nPAYROLL RECORD #{index}")
        print("-" * 40)

        print(f"Employee ID: {record['emp_id']}")
        print(f"Name: {record['name']}")
        print(f"Department: {record['department']}")
        print(f"Basic Salary: Rs. {record['basic_salary']}")
        print(f"Gross Salary: Rs. {record['gross_salary']}")
        print(f"Total Deductions: Rs. {record['total_deductions']}")
        print(f"Net Salary: Rs. {record['net_salary']}")

    print("\n========== END OF HISTORY ==========")


# ==============================
# ANALYTICS AND CHARTS
# ==============================

def salary_analytics():
    print("\n--- SALARY ANALYTICS ---")

    SalaryAnalysis.display_summary()
    SalaryAnalysis.department_analysis()


def generate_charts():
    print("\n--- GENERATING PAYROLL CHARTS ---")

    PayrollCharts.generate_charts()


# ==============================
# MAIN MENU
# ==============================

def display_menu():
    print("\n" + "=" * 45)
    print("       EMPLOYEE PAYROLL MANAGEMENT")
    print("=" * 45)

    print("1.  Add Employee")
    print("2.  View All Employees")
    print("3.  Search Employee")
    print("4.  Update Employee")
    print("5.  Delete Employee")
    print("6.  Process Payroll")
    print("7.  View Payroll History")
    print("8.  Salary Analytics")
    print("9.  Generate Salary Charts")
    print("10. Exit")

    print("=" * 45)



def main():
    init_storage()

    print("\nWelcome to Employee Payroll Management System!")

    while True:
        display_menu()
        choice = input("Enter your choice (1-10): ").strip()

        try:
            if choice == "1":
                add_employee()

            elif choice == "2":
                view_employees()

            elif choice == "3":
                search_employee()

            elif choice == "4":
                update_employee()

            elif choice == "5":
                delete_employee()

            elif choice == "6":
                process_payroll()

            elif choice == "7":
                view_payroll_records()

            elif choice == "8":
                salary_analytics()

            elif choice == "9":
                generate_charts()

            elif choice == "10":
                print("\nThank you for using the Payroll System!")
                break

            else:
                print("Invalid choice. Please select 1-10.")

        except Exception as error:
            print(f"\nUnexpected error: {type(error).__name__}: {error}")
            print("The action was cancelled. Please try again.")

        input("\nPress Enter to return to the main menu...")


if __name__ == "__main__":
    main()
