import pytest

from decimal import Decimal

from analytics import charts

from models.employee import Employee

from storage import csv_manager
from storage.csv_manager import CSVManager


# ==============================
# FIXTURES
# ==============================

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client writing into temporary CSV files."""

    monkeypatch.setattr(csv_manager, "DATA_DIR", tmp_path)
    monkeypatch.setattr(csv_manager, "EMPLOYEE_FILE", tmp_path / "employees.csv")
    monkeypatch.setattr(csv_manager, "PAYROLL_FILE", tmp_path / "payroll.csv")
    monkeypatch.setattr(charts, "CHART_DIR", tmp_path / "charts")

    import app as app_module

    app_module.app.config.update(TESTING=True, SECRET_KEY="test-key")

    with app_module.app.test_client() as test_client:
        yield test_client


def add_employee(emp_id="EMP100", name="Test Employee", salary="30000"):
    CSVManager.save_employee(
        Employee(
            emp_id=emp_id,
            name=name,
            department="Information Technology",
            designation="Developer",
            basic_salary=salary,
        )
    )


PAYROLL_FORM = {
    "hra": "8000",
    "other_allowances": "2000",
    "pf_deduction": "2000",
    "professional_tax": "200",
}


# ==============================
# DASHBOARD
# ==============================

def test_dashboard_renders(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_dashboard_shows_saved_payroll(client):
    add_employee()

    client.post("/payroll/save", data={"emp_id": "EMP100", **PAYROLL_FORM})

    response = client.get("/")

    assert b"Test Employee" in response.data
    assert b"37,800.00" in response.data


# ==============================
# EMPLOYEE MANAGEMENT
# ==============================

def test_add_employee_creates_record(client):
    response = client.post(
        "/employees/add",
        data={
            "emp_id": "EMP200",
            "name": "New Person",
            "department": "Finance",
            "designation": "Analyst",
            "basic_salary": "45000",
        },
    )

    assert response.status_code == 302

    employees = CSVManager.load_employees()
    assert len(employees) == 1
    assert employees[0].name == "New Person"
    assert employees[0].basic_salary == Decimal("45000")


def test_duplicate_employee_id_is_rejected(client):
    form = {
        "emp_id": "EMP201",
        "name": "First Person",
        "department": "Finance",
        "designation": "Analyst",
        "basic_salary": "45000",
    }

    client.post("/employees/add", data=form)

    response = client.post("/employees/add", data=form)

    assert response.status_code == 400
    assert b"Employee ID already exists" in response.data
    assert len(CSVManager.load_employees()) == 1


def test_empty_name_is_rejected(client):
    response = client.post(
        "/employees/add",
        data={
            "emp_id": "EMP202",
            "name": "   ",
            "department": "Finance",
            "designation": "Analyst",
            "basic_salary": "45000",
        },
    )

    assert response.status_code == 400
    assert len(CSVManager.load_employees()) == 0


def test_employee_search_filters_results(client):
    add_employee("EMP300", "Priya Nair")
    add_employee("EMP301", "Rohan Mehta")

    response = client.get("/employees?q=priya")

    assert response.status_code == 200
    assert b"Priya Nair" in response.data
    assert b"Rohan Mehta" not in response.data


def test_edit_employee_updates_salary(client):
    add_employee("EMP400", "Old Name", "30000")

    response = client.post(
        "/employees/EMP400/edit",
        data={
            "name": "Updated Name",
            "department": "Operations",
            "designation": "Manager",
            "basic_salary": "52000",
        },
    )

    assert response.status_code == 302

    employee = CSVManager.load_employees()[0]
    assert employee.name == "Updated Name"
    assert employee.department == "Operations"
    assert employee.basic_salary == Decimal("52000")


def test_delete_employee_removes_record(client):
    add_employee("EMP500", "Delete Me")

    response = client.post("/employees/EMP500/delete")

    assert response.status_code == 302
    assert CSVManager.load_employees() == []


def test_unknown_employee_edit_returns_404(client):
    response = client.get("/employees/DOES-NOT-EXIST/edit")

    assert response.status_code == 404


# ==============================
# PAYROLL
# ==============================

def test_payroll_preview_shows_calculated_net_salary(client):
    add_employee()

    response = client.post("/payroll/new", data={"emp_id": "EMP100", **PAYROLL_FORM})

    assert response.status_code == 200
    # 30000 + 8000 + 2000 = 40000 gross, 2200 deductions, 37800 net
    assert b"40,000.00" in response.data
    assert b"37,800.00" in response.data


def test_payroll_preview_is_not_saved_until_confirmed(client):
    add_employee()

    client.post("/payroll/new", data={"emp_id": "EMP100", **PAYROLL_FORM})

    assert CSVManager.load_payroll_records() == []


def test_payroll_save_persists_record(client):
    add_employee()

    response = client.post("/payroll/save", data={"emp_id": "EMP100", **PAYROLL_FORM})

    assert response.status_code == 302

    records = CSVManager.load_payroll_records()
    assert len(records) == 1
    assert float(records[0]["net_salary"]) == 37800.0


def test_payroll_rejects_negative_amounts(client):
    add_employee()

    response = client.post(
        "/payroll/new",
        data={"emp_id": "EMP100", **PAYROLL_FORM, "hra": "-500"},
    )

    assert response.status_code == 400
    assert CSVManager.load_payroll_records() == []


def test_payroll_history_lists_records(client):
    add_employee()
    client.post("/payroll/save", data={"emp_id": "EMP100", **PAYROLL_FORM})

    response = client.get("/payroll")

    assert response.status_code == 200
    assert b"Test Employee" in response.data
    assert b"37,800.00" in response.data


def test_saved_payslip_page_renders(client):
    add_employee()
    client.post("/payroll/save", data={"emp_id": "EMP100", **PAYROLL_FORM})

    response = client.get("/payroll/1")

    assert response.status_code == 200
    assert b"Employee Payslip" in response.data


# ==============================
# JSON API
# ==============================

def test_api_calculate_returns_net_salary(client):
    add_employee()

    response = client.post(
        "/api/calculate",
        json={"emp_id": "EMP100", **PAYROLL_FORM},
    )

    assert response.status_code == 200

    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["gross_salary"] == "40000"
    assert payload["net_salary"] == "37800"


def test_api_rejects_non_numeric_amount(client):
    add_employee()

    response = client.post(
        "/api/calculate",
        json={"emp_id": "EMP100", **PAYROLL_FORM, "hra": "abc"},
    )

    assert response.status_code == 400
    assert response.get_json()["ok"] is False


# ==============================
# ANALYTICS
# ==============================

def test_analytics_page_renders_chart_images(client):
    add_employee()
    client.post("/payroll/save", data={"emp_id": "EMP100", **PAYROLL_FORM})

    charts.PayrollCharts.clear_cache()

    response = client.get("/analytics")

    assert response.status_code == 200
    assert b"Payroll Analytics" in response.data
    assert b"/charts/salary_comparison.png" in response.data

    # Charts are streamed from memory: no PNG is written to disk.
    chart_dir = charts.CHART_DIR
    assert not (chart_dir / "salary_comparison.png").exists()
    assert not (chart_dir / "department_payroll.png").exists()
    assert not (chart_dir / "salary_distribution.png").exists()


def test_chart_endpoint_streams_png(client):
    add_employee()
    client.post("/payroll/save", data={"emp_id": "EMP100", **PAYROLL_FORM})

    charts.PayrollCharts.clear_cache()

    response = client.get("/charts/salary_comparison.png")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")
    assert not (charts.CHART_DIR / "salary_comparison.png").exists()


def test_unknown_chart_filename_returns_404(client):
    response = client.get("/charts/not-a-chart.png")

    assert response.status_code == 404


def test_chart_without_data_returns_placeholder(client):
    charts.PayrollCharts.clear_cache()

    response = client.get("/charts/department_payroll.png")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")


def test_chart_rendering_error_returns_placeholder(client, monkeypatch):
    add_employee()
    client.post("/payroll/save", data={"emp_id": "EMP100", **PAYROLL_FORM})

    def boom(key, signature=""):
        raise RuntimeError("renderer exploded")

    monkeypatch.setattr(charts.PayrollCharts, "chart_png", staticmethod(boom))

    response = client.get("/charts/salary_distribution.png")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")
