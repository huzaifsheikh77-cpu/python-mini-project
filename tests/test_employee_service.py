
from models.employee import Employee
from services.employee_service import EmployeeService


# 1. Display all employees
print("\nALL EMPLOYEES")

for employee in EmployeeService.get_all_employees():
    employee.display_details()


# 2. Search employee
print("\nSEARCH EMPLOYEE")

employee = EmployeeService.search_employee("EMP001")

if employee:
    employee.display_details()
else:
    print("Employee not found.")


# 3. Update employee
print("\nUPDATE EMPLOYEE")

updated = EmployeeService.update_employee(
    emp_id="EMP001",
    designation="Senior Software Developer",
    basic_salary=35000
)

if updated:
    print("Employee updated successfully.")
    updated.display_details()


# 4. Delete employee
# Uncomment only when you want to test deletion.
#
# deleted = EmployeeService.delete_employee("EMP001")
# print("Employee deleted:", deleted)
