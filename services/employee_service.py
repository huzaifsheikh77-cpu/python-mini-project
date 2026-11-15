from storage.backend import get_store


class EmployeeService:
    """Employee business rules, independent of the storage backend."""

    @staticmethod
    def get_all_employees():
        return get_store().load_employees()

    @staticmethod
    def search_employee(emp_id):
        emp_id = (emp_id or "").strip()

        for employee in get_store().load_employees():
            if employee.emp_id == emp_id:
                return employee

        return None

    @staticmethod
    def add_employee(employee):
        get_store().save_employee(employee)

    @staticmethod
    def update_employee(emp_id, name=None,
                        department=None, designation=None,
                        basic_salary=None):

        return get_store().update_employee(
            emp_id,
            name=name,
            department=department,
            designation=designation,
            basic_salary=basic_salary,
        )

    @staticmethod
    def delete_employee(emp_id):
        return get_store().delete_employee(emp_id)
