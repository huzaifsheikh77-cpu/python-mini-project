"""
Employee Payroll Management System - Flask web application.

Run from the project root:

    python app.py

The site is then available at http://127.0.0.1:5000
"""

import hashlib
import os
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from analytics.charts import ChartUnavailable, PayrollCharts
from analytics.salary_analysis import SalaryAnalysis

from models.employee import Employee
from models.payroll import Payroll

from services.employee_service import EmployeeService
from services.payroll_service import PayrollService

from storage import csv_manager
from storage.backend import StorageError, get_store, init_storage


app = Flask(__name__)

# The secret key is only used to sign the flash-message session cookie.
# It can be overridden with an environment variable, but a working default
# is supplied so the project runs with no extra configuration.
app.config["SECRET_KEY"] = os.environ.get(
    "PAYROLL_SECRET_KEY",
    "payroll-mini-project-development-key",
)


# ==============================
# TEMPLATE HELPERS
# ==============================

@app.template_filter("money")
def money(value):
    """Format a number as 1,23,456.78 style grouped amount."""
    if value is None or value == "":
        return "-"

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)

    if not amount.is_finite():
        return str(value)

    return f"{amount:,.2f}"


def demo_marker_path() -> Path:
    """Path of the marker file that identifies the sample dataset."""
    return csv_manager.DATA_DIR / "DEMO_DATA.txt"


def using_demo_data() -> bool:
    return demo_marker_path().exists()


# ==============================
# DASHBOARD
# ==============================

@app.route("/")
def dashboard():
    employees = EmployeeService.get_all_employees()
    records = PayrollService.history()

    summary = PayrollService.summary(records)
    departments = PayrollService.department_totals(records)

    unprocessed = [
        employee for employee in employees
        if employee.emp_id not in {record["emp_id"] for record in records}
    ]

    return render_template(
        "index.html",
        active="dashboard",
        employees=employees,
        records=records[:5],
        total_records=len(records),
        summary=summary,
        departments=departments,
        unprocessed=unprocessed,
        demo=demo_marker_path().name
        if using_demo_data() else None,
    )


# ==============================
# EMPLOYEE MANAGEMENT
# ==============================

@app.route("/employees")
def employees():
    query = request.args.get("q", "").strip()
    all_employees = EmployeeService.get_all_employees()

    if query:
        needle = query.lower()
        shown = [
            employee for employee in all_employees
            if needle in employee.emp_id.lower()
            or needle in employee.name.lower()
            or needle in employee.department.lower()
            or needle in employee.designation.lower()
        ]
    else:
        shown = all_employees

    return render_template(
        "employees.html",
        active="employees",
        employees=shown,
        total=len(all_employees),
        query=query,
    )


@app.route("/employees/add", methods=["GET", "POST"])
def employee_add():
    if request.method == "POST":
        form = request.form

        try:
            employee = Employee(
                emp_id=form.get("emp_id", ""),
                name=form.get("name", ""),
                department=form.get("department", ""),
                designation=form.get("designation", ""),
                basic_salary=PayrollService.parse_amount(
                    form.get("basic_salary"), "Basic salary", allow_zero=False
                ),
            )

            EmployeeService.add_employee(employee)

        except ValueError as error:
            flash(str(error), "error")
            return render_template(
                "employee_form.html",
                active="employees",
                mode="add",
                form=form,
            ), 400

        flash(f"Employee {employee.name} ({employee.emp_id}) added.", "success")
        return redirect(url_for("employees"))

    return render_template(
        "employee_form.html",
        active="employees",
        mode="add",
        form={},
    )


@app.route("/employees/<path:emp_id>/edit", methods=["GET", "POST"])
def employee_edit(emp_id):
    employee = EmployeeService.search_employee(emp_id)

    if employee is None:
        abort(404)

    if request.method == "POST":
        form = request.form

        name = form.get("name", "").strip() or None
        department = form.get("department", "").strip() or None
        designation = form.get("designation", "").strip() or None

        salary_raw = form.get("basic_salary", "").strip()
        salary = None

        if salary_raw:
            salary = PayrollService.parse_amount(
                salary_raw, "Basic salary", allow_zero=False
            )

        try:
            updated = EmployeeService.update_employee(
                emp_id,
                name=name,
                department=department,
                designation=designation,
                basic_salary=salary,
            )
        except ValueError as error:
            flash(str(error), "error")
            return render_template(
                "employee_form.html",
                active="employees",
                mode="edit",
                employee=employee,
                form=form,
            ), 400

        if updated is None:
            abort(404)

        flash(f"Employee {updated.name} updated.", "success")
        return redirect(url_for("employees"))

    return render_template(
        "employee_form.html",
        active="employees",
        mode="edit",
        employee=employee,
        form={},
    )


@app.route("/employees/<path:emp_id>/delete", methods=["POST"])
def employee_delete(emp_id):
    employee = EmployeeService.search_employee(emp_id)

    if employee is None:
        abort(404)

    EmployeeService.delete_employee(emp_id)

    flash(
        f"Employee {employee.name} ({emp_id}) deleted. "
        "Existing payroll records were kept as history.",
        "success",
    )
    return redirect(url_for("employees"))


# ==============================
# PAYROLL PROCESSING
# ==============================

@app.route("/payroll/new", methods=["GET", "POST"])
def payroll_new():
    employees = EmployeeService.get_all_employees()

    if not employees:
        flash("Add at least one employee before processing payroll.", "error")
        return redirect(url_for("employee_add"))

    if request.method == "POST":
        form = request.form

        try:
            employee = EmployeeService.search_employee(form.get("emp_id", ""))

            if employee is None:
                raise ValueError("Please select a valid employee.")

            payroll = PayrollService.build(employee, form)

        except ValueError as error:
            flash(str(error), "error")
            return render_template(
                "payroll_form.html",
                active="payroll",
                employees=employees,
                form=form,
            ), 400

        return render_template(
            "payslip.html",
            active="payroll",
            payroll=payroll,
            mode="preview",
            record=None,
        )

    return render_template(
        "payroll_form.html",
        active="payroll",
        employees=employees,
        form={},
    )


@app.route("/payroll/save", methods=["POST"])
def payroll_save():
    form = request.form

    try:
        employee = EmployeeService.search_employee(form.get("emp_id", ""))

        if employee is None:
            raise ValueError("Please select a valid employee.")

        payroll = PayrollService.build(employee, form)
        get_store().save_payroll(payroll)

    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("payroll_new"))

    flash(
        f"Payroll saved for {employee.name}. "
        f"Net salary: Rs. {payroll.net_salary:,.2f}",
        "success",
    )
    return redirect(url_for("payroll_history"))


@app.route("/payroll")
def payroll_history():
    records = PayrollService.history()
    summary = PayrollService.summary(records)

    return render_template(
        "history.html",
        active="history",
        records=records,
        summary=summary,
    )


@app.route("/payroll/<int:index>")
def payroll_record(index):
    record = PayrollService.find_record(index)

    if record is None:
        abort(404)

    return render_template(
        "payslip.html",
        active="history",
        payroll=None,
        record=record,
        mode="saved",
    )


# ==============================
# ANALYTICS
# ==============================

@app.route("/analytics")
def analytics():
    df = SalaryAnalysis.load_data()
    summary = SalaryAnalysis.summary(df) if df is not None else None
    departments = SalaryAnalysis.department_summary(df) if df is not None else []

    try:
        signature = get_store().data_signature()
    except StorageError:
        signature = "unavailable"

    chart_urls = {
        key: url_for("chart_image", filename=name)
        for key, name in PayrollCharts.CHART_FILES.items()
    }

    return render_template(
        "analytics.html",
        active="analytics",
        summary=summary,
        departments=departments,
        chart_urls=chart_urls,
        cache_token=hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12],
    )


@app.route("/charts/<path:filename>")
def chart_image(filename):
    """Render a chart in memory and stream it; nothing is written to disk."""

    key = PayrollCharts.key_for_filename(filename)

    if key is None:
        abort(404)

    try:
        signature = get_store().data_signature()
    except StorageError:
        signature = "unavailable"

    try:
        data = PayrollCharts.chart_png(key, signature)

    except ChartUnavailable:
        return send_file(
            BytesIO(PayrollCharts.placeholder_png("No payroll records to chart yet")),
            mimetype="image/png",
            max_age=0,
        )

    except Exception as error:
        app.logger.exception("Chart rendering failed: %s", error)

        return send_file(
            BytesIO(PayrollCharts.placeholder_png("This chart could not be generated")),
            mimetype="image/png",
            max_age=0,
        )

    return send_file(BytesIO(data), mimetype="image/png", max_age=0)


# ==============================
# JSON API (live salary preview)
# ==============================

@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    data = request.get_json(silent=True) or {}

    try:
        employee = EmployeeService.search_employee(str(data.get("emp_id", "")))

        if employee is None:
            raise ValueError("Please select a valid employee.")

        payroll = PayrollService.build(employee, data)

    except ValueError as error:
        return jsonify({"ok": False, "error": str(error)}), 400

    return jsonify(
        {
            "ok": True,
            "emp_id": employee.emp_id,
            "name": employee.name,
            "basic_salary": str(employee.basic_salary),
            "gross_salary": str(payroll.gross_salary),
            "total_deductions": str(payroll.total_deductions),
            "net_salary": str(payroll.net_salary),
        }
    )


# ==============================
# ERROR HANDLERS
# ==============================

@app.errorhandler(StorageError)
def storage_unavailable(error):
    """Database down, misconfigured or schema missing."""

    app.logger.error("Storage error: %s", error)

    return render_template(
        "error.html",
        active="",
        code=503,
        title="Database unavailable",
        message="The payroll database could not be reached. "
        "Check the DATABASE_URL setting and the terminal running app.py.",
    ), 503


@app.errorhandler(404)
def not_found(error):
    return render_template(
        "error.html",
        active="",
        code=404,
        title="Page not found",
        message="The page or record you requested does not exist.",
    ), 404


@app.errorhandler(500)
def server_error(error):
    return render_template(
        "error.html",
        active="",
        code=500,
        title="Unexpected error",
        message="The request could not be completed. "
        "Check the terminal running app.py for details.",
    ), 500


# ==============================
# ENTRY POINT
# ==============================

if __name__ == "__main__":
    init_storage()

    # Debug only for local runs; production (Vercel) imports the WSGI app and
    # never reaches app.run(). Set PAYROLL_DEBUG=0 to disable it locally.
    debug = os.environ.get("PAYROLL_DEBUG", "1").strip() == "1"

    print("\nEmployee Payroll Management System")
    print(f"Open http://127.0.0.1:5000 in your browser. (debug={debug})")
    print("Press CTRL+C to stop the server.\n")

    app.run(host="127.0.0.1", port=5000, debug=debug)
