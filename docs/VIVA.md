# Viva Preparation - 60 Questions with Answers

All answers match the source code in this repository. Section 1 is the general project
viva; sections 2-6 are the focused question sets.

---

## Section 1 - 30 likely project viva questions

**1. What is your project about?**
It is an Employee Payroll Management System. It stores employee records, calculates gross
salary, deductions and net salary, generates payslips, keeps a permanent payroll history
and shows salary analytics with charts. It runs as a Flask website on the local machine and
also has a console version.

**2. Why did you choose this project?**
Payroll is a real administrative task with clear rules (earnings, deductions, net pay), so
the logic can be verified by hand. It also needs file storage, validation, reporting and a
user interface - which covers most of the syllabus in one project.

**3. Which modules make up the project?**
Six packages plus two entry points. `models/` (Employee, Payroll), `services/` (employee
and payroll business rules), `storage/` (CSV access), `analytics/` (Pandas analysis and
Matplotlib charts), `templates/` and `static/` (the web interface), and the entry points
`app.py` (website) and `main.py` (console).

**4. What is the entry point of the website?**
`app.py`. Running `python app.py` creates the Flask application object, creates the data
files if they are missing, and starts the development server on `http://127.0.0.1:5000`.

**5. How is an employee stored?**
The Add Employee form posts to the route `employee_add`, which builds an `Employee` object
(validation runs in `__post_init__`) and calls `EmployeeService.add_employee()`. That calls
`CSVManager.save_employee()`, which checks for a duplicate ID and appends one row to
`data/employees.csv`.

**6. What happens when you click "Save payroll record"?**
The form posts to `/payroll/save`. The route loads the employee, rebuilds the `Payroll`
object from the submitted amounts, and calls `CSVManager.save_payroll()`, which appends one
row - basic salary, HRA, allowances, PF, tax, gross, total deductions and net salary - to
`data/payroll.csv`. Then the user is redirected to the payroll history with a success
message.

**7. How do you stop the same employee ID being added twice?**
`CSVManager.save_employee()` loads the current employees first and raises
`ValueError("Employee ID already exists.")` if the ID is already present. The route catches
that error and shows it on the form with HTTP status 400. There is also a test for it.

**8. Where is the data stored, and why not a database?**
In two CSV files, `data/employees.csv` and `data/payroll.csv`. A mini project with tens of
records does not need a database server, and CSV files can be opened in Excel and inspected
during a demonstration. A database would be the next step for concurrent or large-scale
use; this is listed as a limitation.

**9. What does each folder do?**
`models` holds the data classes and their validation, `services` holds the business rules,
`storage` is the only place that touches files, `analytics` does the reporting, `templates`
and `static` are the web interface, `data` and `charts` hold generated files, `scripts`
holds the data reset utility, `docs` holds the documentation and `tests` holds the
automated tests.

**10. What is the difference between the Employee class and the Payroll class?**
`Employee` is master data: ID, name, department, designation and basic salary. `Payroll`
is one monthly transaction for an employee: HRA, allowances, PF and tax, plus the computed
gross, deductions and net salary. A `Payroll` object contains an `Employee` object.

**11. How does the dashboard get its numbers?**
The `dashboard()` route calls `EmployeeService.get_all_employees()`,
`PayrollService.history()` and `PayrollService.summary(records)`, then passes the values to
`templates/index.html`. Totals are added with `Decimal`, and department totals are grouped
by the `department` key of each payroll row.

**12. How does search work?**
The search box submits a GET request with `?q=text`. The `employees()` route reads it with
`request.args.get("q")` and keeps employees whose ID, name, department or designation
contains the text, case-insensitively.

**13. Why does editing an employee rewrite the whole file?**
A CSV file is sequential - you cannot overwrite one row in place without shifting the
others. So `EmployeeService.update_employee()` loads all employees, replaces the matching
object in the list, and `CSVManager.replace_employees()` writes the whole file back with a
fresh header.

**14. What happens to payroll records when an employee is deleted?**
They are kept. A payroll row already stores the name, department and basic salary at the
time of processing, so it remains a valid financial record and is still visible in Payroll
History. The delete confirmation message states this.

**15. What validations are implemented?**
Employee ID, name, department and designation cannot be empty or blank; basic salary must
be numeric, finite and greater than zero; HRA, allowances, PF and tax must be numeric,
finite and not negative; deductions may not exceed the gross salary; and the selected
employee must exist. The rules live in the model and in
`PayrollService.parse_amount()`.

**16. What happens if you type a negative or alphabetic salary?**
The browser may block some input, but the server is the real check:
`PayrollService.parse_amount()` raises `ValueError` ("must be a number", "cannot be
negative"), the route catches it, flashes the message and returns the form with status 400.
If a negative value somehow reached the model, `__post_init__` would also reject it.

**17. What happens if deductions exceed the gross salary?**
`Payroll.__post_init__` raises `ValueError("Deductions cannot exceed gross salary.")`. This
guarantees net salary can never be negative, and there is a unit test
(`test_deductions_cannot_exceed_gross_salary`) for it.

**18. How are errors handled in the web application?**
Expected problems (bad input, duplicate ID, unknown employee) are raised as `ValueError`,
caught in the route and shown as a message on the form with HTTP 400. An unknown URL or
missing record calls `abort(404)` and is rendered by the `404` error handler; unexpected
failures use the `500` handler. Both render `templates/error.html` instead of showing a
stack trace to the user.

**19. How is the payslip generated?**
The `Payroll` object's properties (`gross_salary`, `total_deductions`, `net_salary`) are
rendered by `templates/payslip.html`, which shows earnings in one column and deductions in
another. The same object can print a text payslip through `Payroll.generate_payslip()` in
the console version, so both front ends produce identical figures.

**20. Where are the charts created and stored?**
`analytics/charts.py` builds them with Matplotlib, but in the web application they are
rendered **in memory** and streamed from `/charts/<filename>` as PNG responses - nothing is
written to disk, which is required on Vercel. Rendered images are cached in memory until the
payroll data changes, and a placeholder image is returned if a chart cannot be drawn. The
console version still writes the three PNG files into `charts/` for offline use.

**21. What are the limitations of the project?**
No login or user roles; single-user CSV storage with no locking; no pay-period (month) field
in payroll records; no PDF or e-mailed payslips; allowances and tax are typed manually
instead of derived from percentages; the Flask development server is used rather than a
production server; no audit trail for edits; and charts are static images.

**22. What would you add next?**
A pay-period column with month-wise reports, migration to SQLite, login with roles, PDF
payslip generation, percentage-based salary rules, attendance and leave, CSV/Excel export,
interactive charts, and deployment behind a production WSGI server.

**23. How is the project tested, and how many tests are there?**
With pytest: `python -m pytest tests/ -v`. There are **53 automated tests** in five files -
3 for the employee model, 5 for salary calculation, 5 for CSV persistence, 22 for the web
routes, JSON API and chart responses, and 18 for the PostgreSQL repository and CSV
migration - and all 53 pass. The web and storage tests run against temporary files or a throw-away test database,
so real data is never modified.

**24. Why keep both a console version and a website?**
They satisfy different requirements: the console version proves the core logic works
without a browser and is easy to demonstrate in a terminal, while the website is the
deliverable users expect. Both call the same models, services and storage code, which also
proves the design is properly layered - no logic was duplicated.

**25. How would you run this for real users?**
Replace `app.run(debug=True)` with a production WSGI server such as Waitress on Windows or
Gunicorn on Linux, turn off debug mode, move data into a database with transactions, add
authentication, and serve over HTTPS. As submitted, it is a local demonstration
application only.

**26. What is the purpose of requirements.txt?**
It pins the exact versions of the third-party packages the project needs - Flask, Pandas,
Matplotlib, pytest and their dependencies - so that `pip install -r requirements.txt`
reproduces the same environment on any machine.

**27. What is a virtual environment and why use one?**
A folder (`.venv`) containing a private copy of the Python interpreter's packages. It keeps
this project's versions separate from other projects and from the system Python, so
upgrading one project cannot break another, and `requirements.txt` describes exactly that
environment.

**28. Which part was the most difficult, and which are you most satisfied with?**
The most difficult part was keeping the money arithmetic exact and consistent across the
CLI, the web forms and the CSV file - solved by converting every amount to `Decimal` at the
boundary and by computing gross, deductions and net as properties instead of storing them
in three places. The most satisfying part is that the preview shown while typing is
produced by the same class that saves the record, so the displayed net salary is always the
saved one.

**29. What happens if two people save payroll at the same time?**
Nothing protects against it - CSV files have no locking, so two simultaneous writers could
lose one record or interleave. This is documented as a limitation and is acceptable for a
single-user local application; a database with transactions would be the fix.

**30. What did you learn from this project?**
How to structure a Python program in layers so one core can serve a CLI and a web
interface; how Flask routes, templates and form handling fit together; why `Decimal` is
required for money; how CSV files are read, appended and rewritten; how Pandas and
Matplotlib turn stored data into reports; and how automated tests with `tmp_path` let you
test file-based code without damaging real data.

---

## Section 2 - 10 questions on Python OOP

**1. What is Object-Oriented Programming, and what are its four pillars?**
OOP organises a program around objects that combine data with the operations on that data.
The four pillars are encapsulation (data and rules together), abstraction (hiding
details behind a simple interface), inheritance (reusing a parent class) and polymorphism
(one interface, many implementations).

**2. What is the difference between a class and an object in your project?**
A class is the blueprint - `Employee` describes what an employee has. An object is one
actual instance - the employee Aditya Sharma with ID EMP001. `EmployeeService.get_all_employees()`
returns a list of `Employee` *objects* built from the CSV rows.

**3. What is a dataclass and why did you use it?**
`@dataclass` (from the standard library `dataclasses` module) generates `__init__`,
`__repr__` and `__eq__` from the declared fields. So `Employee(emp_id=..., name=..., ...)`
works without writing a constructor, and the class stays short and readable.

**4. What is `__post_init__` and what does it do here?**
It is a dataclass hook that runs automatically at the end of the generated `__init__`. In
`Employee` it strips whitespace from the text fields, converts `basic_salary` to `Decimal`,
and raises `ValueError` for empty or invalid values. In `Payroll` it normalises the four
amounts to `Decimal` and validates them.

**5. Where is encapsulation demonstrated?**
In the models. The data (`basic_salary`, `hra`, ...) and the rules that keep it valid live
in the same class, and validation runs inside `__post_init__`, so it is impossible to
construct an `Employee` without a name or a `Payroll` with a negative net salary. Outside
code cannot create an invalid object even by mistake.

**6. What is composition, and where is it used?**
Composition means an object *has* another object instead of inheriting from it.
`Payroll` has an `employee` attribute of type `Employee` and reads
`self.employee.basic_salary`, `self.employee.name` and so on. A payroll transaction cannot
exist without its employee.

**7. What is a property? Give an example from your code.**
A property is a method accessed like an attribute. `Payroll.gross_salary` is decorated with
`@property` and returns `basic + hra + other_allowances`. The template writes
`payroll.gross_salary` without parentheses, and the value is recomputed from the components
each time, so it can never disagree with them.

**8. What is a static method, and why are your services written that way?**
A `@staticmethod` belongs to the class but receives neither `self` nor `cls` - it is a
grouped utility function. `CSVManager`, `EmployeeService`, `PayrollService` and
`SalaryAnalysis` hold no per-object state, so static methods express "these operations
belong to this responsibility" without forcing the caller to create an instance.

**9. Do you use inheritance? Why not?**
No. Every entity is a concrete class and the layers communicate through plain objects, so
there is no shared parent behaviour that needs to be factored out. OOP is demonstrated
through classes, objects, encapsulation, composition, properties and abstraction.
Inheritance would be a natural extension - for example `Employee` as a base class with
`Manager` and `Intern` subclasses that override allowance rules.

**10. What is the difference between a class attribute and an instance attribute here?**
An instance attribute belongs to one object - `employee.name`, `payroll.hra`. A class-level
constant belongs to the module/class - `csv_manager.EMPLOYEE_FILE` and
`csv_manager.PAYROLL_FILE` are defined once and shared. Because they are read inside the
methods at call time, tests can `monkeypatch` them to temporary paths.

---

## Section 3 - 5 questions on Flask and web architecture

**1. What is Flask, and why did you choose it over Django?**
Flask is a micro web framework: it provides URL routing and request/response handling and
leaves templates, database and structure to the developer. For a project with about a dozen
pages it is far lighter than Django, which assumes an ORM, an admin site and a fixed project
layout. Flask also makes the request flow easy to explain in a viva.

**2. How does routing work in your application?**
A route is a decorator that binds a URL to a Python function:
`@app.route("/employees/add", methods=["GET", "POST"])`. GET shows the empty form, POST
processes it - one function handles both by testing `request.method`. Variable rules such as
`/employees/<path:emp_id>/edit` capture part of the URL and pass it to the function as an
argument.

**3. How are the pages produced? What is Jinja2?**
Flask uses the Jinja2 template engine. `render_template("employees.html", employees=...)`
fills placeholders in an HTML file with Python values. Every page extends `base.html`
(`{% extends %}` + `{% block content %}`), so the navigation and layout exist once. A custom
filter `money` formats amounts, and `url_for()` generates URLs from function names so links
never hard-code paths.

**4. How does the browser communicate with the backend?**
Two ways. (a) Normal HTML form submission: `method="post"` sends
`application/x-www-form-urlencoded` data, the route reads it with `request.form`, and the
response is either re-rendered HTML (HTTP 400 on invalid input) or a 302 redirect to
another page. (b) One JSON call: the payroll form's JavaScript `fetch()`s
`/api/calculate`, and Flask answers with `jsonify({...})`. Search uses `request.args` for
`?q=`. All pages are rendered on the server; there is no single-page application.

**5. What are flash messages, `url_for` and error handlers? What about debug mode?**
`flash("Payroll saved", "success")` stores a one-time message in the signed session cookie,
which `base.html` reads with `get_flashed_messages()` and shows once - it survives the
redirect after a POST, which prevents duplicate submissions on refresh. `url_for()` builds
URLs from endpoint names. `@app.errorhandler(404)` and `(500)` render `error.html` instead of
a raw error. `app.run(debug=True)` is convenient during development but must never be
exposed publicly, because it reveals source and an interactive debugger - hence the project
is a local demonstration, not a deployment.

---

## Section 4 - 5 questions on CSV and data persistence

**1. Why did you use CSV files instead of a database?**
Because the dataset is small and the files are portable, human-readable and openable in
Excel, which makes the storage easy to demonstrate. CSV also needs no server process. The
trade-off is no transactions, no locking and no indexing - documented as a limitation, with
SQLite suggested as the next step.

**2. How is a new record written?**
`CSVManager.save_employee()` / `save_payroll()` open the file in append mode
(`open("a", newline="", encoding="utf-8")`), pass the handle to `csv.writer(...)` and write
one list of values. Existing rows are never touched, so an append cannot corrupt earlier
records.

**3. How is data read back?**
With `csv.DictReader`, which takes the first line as column names and yields one dictionary
per row. `load_employees()` converts each dictionary into a validated `Employee` object, and
`load_payroll_records()` returns the dictionaries directly because payroll rows are only
displayed and totalled.

**4. How are rows updated and deleted, since CSV has no UPDATE?**
By rewriting the file. The service loads every employee, replaces the matching object (or
filters it out), and `replace_employees()` writes the header plus all remaining rows into the
same file, overwriting it. Payroll records are never rewritten, because they are financial
history.

**5. What problems can CSV storage cause, and how are they handled?**
No locking, so simultaneous writers can lose data (documented limitation);
`newline=""` and `encoding="utf-8"` avoid blank lines and broken characters on Windows;
stored values are always text, so each row is converted and re-validated on load; there is no
schema enforcement, so an unreadable file is reported instead of silently ignored; and scale
is limited to about thousands of rows, which is why a database is the recommended upgrade.

---

## Section 5 - 5 questions on payroll calculations and Decimal

**1. Write the salary formulas used in your project.**
Gross salary = basic salary + HRA + other allowances. Total deductions = PF + professional
tax. Net salary = gross salary - total deductions. They are implemented as the
`gross_salary`, `total_deductions` and `net_salary` properties of `Payroll`.

**2. Calculate a salary using the project's numbers.**
Basic 32,000, HRA 25,000, other allowances 10,000: gross = 67,000. PF 7,000 + professional
tax 200 = 7,200 deductions. Net = 67,000 - 7,200 = **59,800**, which is exactly what the
live preview and the saved payslip show.

**3. Why use `Decimal` instead of `float` for money?**
`float` stores values in binary, so many decimal fractions cannot be represented exactly:
`0.1 + 0.2` gives `0.30000000000000004`, and adding lakhs of rupees accumulates a visible
paisa error. `Decimal` works in base ten, so `Decimal("0.1") + Decimal("0.2")` is exactly
`Decimal("0.3")`, and comparisons such as "deductions equal gross" behave predictably.

**4. How do you convert and round values safely?**
Every value is converted with `Decimal(str(value))` - the `str()` step avoids inheriting a
float's binary error. Averaging is rounded explicitly with
`quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`, the same half-up rule used for currency,
and display formatting uses `f"{amount:,.2f}"`.

**5. How is a negative net salary prevented?**
`Payroll.__post_init__` rejects any negative component and raises
`ValueError("Deductions cannot exceed gross salary.")` when
`pf_deduction + professional_tax > gross_salary`. `PayrollService.parse_amount()` blocks
non-numeric, infinite and negative input before the object is even created, and the rule is
covered by an automated test.

---

## Section 6 - 5 questions on Pandas, Matplotlib and testing

**1. What is Pandas, and how is it used here?**
Pandas is a data analysis library that represents tabular data as a DataFrame with labelled
columns. `SalaryAnalysis.load_data()` reads `payroll.csv` with
`pd.read_csv(csv_manager.PAYROLL_FILE)` and then uses column operations, `sum()`, `mean()`,
`max()` and `min()` to produce the summary figures shown on the Analytics page.

**2. What is a DataFrame and what is a Series?**
A DataFrame is a two-dimensional table with named columns; here each row is one payroll
transaction and the columns are `emp_id`, `name`, `net_salary` and so on. A Series is a
single column of that table, such as `df["net_salary"]`, which is what `.sum()` or `.mean()`
is applied to.

**3. How does the department analysis work?**
`df.groupby("department").agg(employees=("net_salary","size"), total=("net_salary","sum"), average=("net_salary","mean")).sort_values("total", ascending=False)`
groups the rows by department, computes three aggregates per group, and sorts by total
payout, giving the department table on the Analytics page.

**4. How are the Matplotlib charts produced?**
`analytics/charts.py` draws a bar chart of net salary per employee, a pie chart of
department payout share and a histogram of salary distribution. The `Agg` backend is
selected at import so charts render without a display - essential on a web server. Each
request builds a `Figure` on a `FigureCanvasAgg`, saves it into a `BytesIO` buffer and the
`/charts/<filename>` route streams those bytes as `image/png`; no file is written, so the
same code works on Vercel's read-only filesystem. Results are cached in memory per data
signature, and a placeholder PNG is returned if rendering fails. The console version still
writes PNG files into `charts/`.

**5. What testing was done, and how do you know 53 tests really pass?**
`python -m pytest tests/ -v` reports **53 passed**. The tests cover model validation (3),
salary calculation (5), CSV persistence (5), the web layer (22: every route, the payroll
preview/save flow, duplicate and negative input, the 404 page, the JSON API, and the
in-memory chart responses including the 404 and placeholder paths) and the database layer
(18: repository CRUD, history integrity, Decimal
precision, reconnect persistence, connection errors and the CSV migration). Storage and web
tests use pytest's `tmp_path` with `monkeypatch` to redirect
the CSV and chart paths to a temporary folder, so running the suite never changes
`data/employees.csv` or `data/payroll.csv`; the web tests use Flask's `test_client()` and
need no running server.

---

## Quick revision sheet

| Item | Value |
| --- | --- |
| Entry points | `app.py` (web), `main.py` (console) |
| Framework | Flask 3.1.3 + Jinja2 |
| Money type | `decimal.Decimal`, `ROUND_HALF_UP` for averages |
| Storage | `data/employees.csv`, `data/payroll.csv` |
| Analysis | Pandas 3.1.1 (`read_csv`, `groupby`, `sum`, `mean`) |
| Charts | Matplotlib 3.11.2, `Agg` backend, PNG streamed from memory |
| Tests | 53 pytest tests, all passing |
| Sample data | 6 employees, 5 payroll records (`scripts/reset_data.py --demo`) |
| Verdict | Ready for local demonstration; not deployed |
