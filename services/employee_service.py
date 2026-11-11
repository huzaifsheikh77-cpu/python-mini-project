
from models.employee import Employee
from storage.csv_manager import CSVManager


class EmployeeService:

    @staticmethod
    def get_all_employees():
        return CSVManager.load_employees()

    @staticmethod
    def search_employee(emp_id):
        emp_id = emp_id.strip()

        employees = CSVManager.load_employees()

        for employee in employees:
            if employee.emp_id == emp_id:
                return employee

        return None

    @staticmethod
    def add_employee(employee):
        CSVManager.save_employee(employee)

    @staticmethod
    def update_employee(emp_id, name=None,
                        department=None, designation=None,
                        basic_salary=None):

        employees = CSVManager.load_employees()

        for index, employee in enumerate(employees):

            if employee.emp_id == emp_id:

                updated_employee = Employee(
                    emp_id=employee.emp_id,
                    name=name if name is not None else employee.name,
                    department=department if department is not None else employee.department,
                    designation=designation if designation is not None else employee.designation,
                    basic_salary=basic_salary if basic_salary is not None else employee.basic_salary
                )

                employees[index] = updated_employee

                CSVManager.replace_employees(employees)

                return updated_employee

        return None

    @staticmethod
    def delete_employee(emp_id):
        employees = CSVManager.load_employees()

        updated_employees = [
            employee for employee in employees
            if employee.emp_id != emp_id
        ]

        if len(updated_employees) == len(employees):
            return False

        CSVManager.replace_employees(updated_employees)

        return True
