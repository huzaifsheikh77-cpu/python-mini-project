# Project Explanation - Employee Payroll Management System

A technical explanation of how the project is built, written to match the actual source
code in this repository. Every claim below can be checked in the named file.

---

## 1. Why Python was used

1. **Readable syntax.** A payroll rule such as
   `net = gross - deductions` is written almost as it sounds, so the logic can be
   explained and marked easily.
2. **Real object-oriented support.** Python has classes, dataclasses, properties and
   exceptions, which is exactly what an OOP-based mini project must demonstrate
   (`models/employee.py`, `models/payroll.py`).
3. **Standard library covers the basics.** The `csv` module handles file storage and the
   `decimal` module handles money - no external library is needed for either
   (`storage/csv_manager.py`, `models/payroll.py`).
4. **The analytics libraries exist for Python.** Pandas (data analysis) and Matplotlib
   (charts) are the standard tools for tabular analysis and graphs, so the same language
   covers the application *and* the reporting (`analytics/`).
5. **One language for console and web.** The same core runs under a terminal menu
   (`main.py`) and under a browser (`app.py`) without rewriting it.
6. **Easy to install and demonstrate.** `python -m venv` plus one requirements file is
   enough for any laptop.

---

## 2. How Flask works in this application

Flask is a **micro web framework**: it provides routing and request handling, and leaves
everything else to us. The whole web layer is `app.py` plus the templates.

**a. The application object**

```python
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("PAYROLL_SECRET_KEY",
                                          "payroll-mini-project-development-key")
```

`Flask(__name__)` tells Flask where the application lives, so it can find `templates/`
and `static/` automatically. The secret key is used only to sign the flash-message
cookie. A default is provided, so **no environment variable has to be set**; the
environment variable exists only as an override.

**b. Routes map a URL to a Python function**

```python
@app.route("/payroll/save", methods=["POST"])
def payroll_save():
    ...
```

| URL | Method | Function | Purpose |
| --- | --- | --- | --- |
| `/` | GET | `dashboard` | Dashboard |
| `/employees` | GET | `employees` | List + search (`?q=`) |
| `/employees/add` | GET, POST | `employee_add` | Add form / create |
| `/employees/<emp_id>/edit` | GET, POST | `employee_edit` | Edit form / update |
| `/employees/<emp_id>/delete` | POST | `employee_delete` | Delete |
| `/payroll/new` | GET, POST | `payroll_new` | Payroll form / payslip preview |
| `/payroll/save` | POST | `payroll_save` | Append the record to CSV |
| `/payroll` | GET | `payroll_history` | History |
| `/payroll/<index>` | GET | `payroll_record` | One saved payslip |
| `/analytics` | GET | `analytics` | Pandas summary + charts |
| `/charts/<filename>` | GET | `chart_image` | Render a chart in memory and stream it as PNG |
| `/api/calculate` | POST | `api_calculate` | JSON salary preview |

The `<emp_id>` and `<int:index>` parts are **variable rules**: Flask passes them to the
function as arguments.

**c. Reading the request**

- `request.form` holds the submitted HTML form fields (`request.form.get("hra")`).
- `request.args` holds the query string (`request.args.get("q", "")` for search).
- `request.get_json(silent=True)` reads a JSON body for `/api/calculate`.

**d. Producing the response**

- `render_template("payslip.html", payroll=payroll, ...)` renders a Jinja2 template and
  returns HTML. Templates inherit a common layout (`{% extends "base.html" %}` in every
  page) and use template filters such as `{{ amount|money }}`, registered in `app.py`.
- `redirect(url_for("payroll_history"))` returns an HTTP 302 after a successful POST.
  `url_for()` builds the URL from the function name, so links do not break when a route
  changes.
- `jsonify({...})` returns JSON for the live-calculation endpoint.
- `abort(404)` raises the 404 error, which `@app.errorhandler(404)` renders as a friendly
  page instead of a stack trace.

**e. Flash messages**

After a save, `flash("Payroll saved for ...", "success")` stores a one-time message in the
signed session cookie. `base.html` reads it with `get_flashed_messages(with_categories=true)`
and displays it once. This is why the secret key is needed.

**f. Development server**

```python
app.run(host="127.0.0.1", port=5000, debug=True)
```

`127.0.0.1` binds the server to the local machine only. `debug=True` shows errors in the
browser and auto-restarts on code changes. **This is a development server, not a
production web server.**

**g. Thin controller, thick model**

No salary arithmetic is written inside a route. Routes validate the request, call
`EmployeeService` / `PayrollService` / `CSVManager`, and choose a template. All rules stay
in the model and service layer, so the console version behaves identically.

---

## 3. How the Employee and Payroll classes are used

### `Employee` - `models/employee.py`

```python
@dataclass
class Employee:
    emp_id: str
    name: str
    department: str
    designation: str
    basic_salary: Decimal
```

- `@dataclass` generates the constructor, so `Employee(emp_id=..., name=..., ...)` is
  available without writing `__init__`.
- `__post_init__()` runs automatically after construction. It strips whitespace from text
  fields, converts `basic_salary` to `Decimal`, and raises `ValueError` for an empty ID,
  empty name, empty department, empty designation, non-finite salary or a salary that is
  not positive. **A wrongly built Employee object therefore cannot exist.**
- `display_details()` prints one employee in a formatted block; the console menu uses it.
  The website renders the same data through `templates/employees.html` instead.

### `Payroll` - `models/payroll.py`

```python
@dataclass
class Payroll:
    employee: Employee
    hra: Decimal = Decimal("0")
    other_allowances: Decimal = Decimal("0")
    pf_deduction: Decimal = Decimal("0")
    professional_tax: Decimal = Decimal("0")
```

- It **contains** an `Employee` object (`payroll.employee.name`), i.e. **composition**: a
  payroll transaction cannot exist without the employee it belongs to.
- `__post_init__()` normalises every amount with `Decimal(str(value))`, rejects negative
  amounts, and rejects the case `pf + tax > gross_salary` with
  `ValueError("Deductions cannot exceed gross salary.")`.
- Three `@property` methods expose the calculated money: `gross_salary`,
  `total_deductions`, `net_salary`. They are computed on access, so they can never drift
  out of sync with the stored components.
- `generate_payslip()` prints the payslip in the terminal (used by the console version).
  The website produces the same information from the same object in `templates/payslip.html`.

### Where they are created

| Situation | Code |
| --- | --- |
| Web: add employee | `app.py` -> `employee_add()` builds `Employee`, then `EmployeeService.add_employee()` |
| Web: payroll preview/save | `PayrollService.build(employee, form)` creates `Payroll` |
| Console | `main.py` -> `add_employee()`, `process_payroll()` |
| Reading the CSV back | `CSVManager.load_employees()` rebuilds `Employee` objects, so validation runs on stored data too |
| Tests | fixtures build `Employee` and `Payroll` directly |

---

## 4. How OOP concepts are demonstrated

| Concept | Where | Explanation |
| --- | --- | --- |
| **Class and object** | `Employee`, `Payroll`, `CSVManager`, `EmployeeService`, `PayrollService`, `SalaryAnalysis`, `PayrollCharts` | Every entity and every layer is a class; objects are created per employee/payroll |
| **Encapsulation** | `Employee.__post_init__`, `Payroll.__post_init__` | Data and the rules that protect it live in one place; an invalid object cannot be constructed |
| **Composition** | `Payroll.employee` | A `Payroll` *has-a* `Employee` rather than duplicating employee fields |
| **Abstraction** | `services/`, `storage/` | Routes and the CLI call `EmployeeService` / `CSVManager` and never touch CSV details |
| **Computed properties** | `Payroll.gross_salary`, `total_deductions`, `net_salary` | Read-only values derived from the components; no duplicated stored state |
| **Methods** | `Employee.display_details()`, `Payroll.generate_payslip()` | Behaviour belongs to the object that owns the data |
| **Static methods / utility classes** | `CSVManager`, `EmployeeService`, `PayrollService`, `SalaryAnalysis` | Stateless operations grouped by responsibility (`@staticmethod`) |
| **Class-level constants** | `csv_manager.EMPLOYEE_FILE`, `csv_manager.PAYROLL_FILE`, `charts.CHART_DIR` | Paths defined once and reused |
| **Single responsibility** | six modules | Models store and validate, services apply business rules, storage writes files, analytics reports |
| **Exception-based error handling** | `ValueError` raised in models/services, caught in routes | Errors are signalled by exceptions and handled at the boundary |

**Honest note for the viva:** *inheritance and polymorphism are not used* in this project.
There is no class hierarchy such as `Person -> Employee -> Manager`, because every entity
is a concrete dataclass and the layers communicate through plain objects. OOP is
demonstrated through classes, objects, encapsulation, composition, properties and
abstraction. Inheritance would be a natural next step (for example
`Employee -> Manager` with extra allowance rules).

---

## 5. How CSV storage works

`storage/csv_manager.py` is the **only** module that reads or writes files.

**File creation**

```python
DATA_DIR = BASE_DIR / "data"          # absolute, based on the module location
EMPLOYEE_FILE = DATA_DIR / "employees.csv"
PAYROLL_FILE  = DATA_DIR / "payroll.csv"
```

`BASE_DIR` is derived from `Path(__file__)`, so the data folder is always found correctly
no matter which directory the program is started from. `initialize_files()` creates the
folder and both files with a header row if they are missing, and is called on application
start.

**Writing a new record (append)**

```python
with EMPLOYEE_FILE.open("a", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow([employee.emp_id, employee.name, ...])
```

Appending is O(1) and never risks the existing rows. Before appending, `save_employee()`
loads the file and rejects a duplicate ID with `ValueError("Employee ID already exists.")`.

**Reading (dictionary style)**

```python
with EMPLOYEE_FILE.open("r", newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        employees.append(Employee(emp_id=row["emp_id"], ...))
```

`DictReader` uses the first line as keys, so each row becomes a dictionary - readable and
immune to column-order changes. Each row is turned back into a validated `Employee`
object, which means corrupted data fails loudly instead of silently propagating.

**Updating and deleting**

CSV cannot update a row in place, so `replace_employees()` rewrites the whole file: the
service loads all employees, replaces or filters the list in memory, and writes everything
back with a fresh header. Deleting is the same list comprehension without the id.

**Details that matter on Windows**

- `newline=""` prevents the `csv` module from producing blank lines between rows on
  Windows.
- `encoding="utf-8"` keeps non-ASCII names intact.
- Payroll rows are appended, never rewritten, because they are financial history.

---

## 6. Why Decimal is used for money

`float` stores numbers in binary, so many decimal values cannot be represented exactly:

```python
>>> 0.1 + 0.2
0.30000000000000004
>>> 2200.10 + 200.20
2400.3000000000003
```

For a salary of lakhs of rupees, such errors become visible paisa differences and failed
comparisons. `Decimal` stores the digits in **base 10**, exactly as written, so:

```python
>>> Decimal("2200.10") + Decimal("200.20")
Decimal('2400.30')
```

**How it is used in this project**

- `Employee.__post_init__` converts the basic salary immediately:
  `self.basic_salary = Decimal(str(self.basic_salary))`.
- `Payroll.__post_init__` converts each of the four components the same way, so a form
  string, an int or a float all end up as an exact `Decimal`.
- All three properties use `Decimal` arithmetic only.
- The average in `PayrollService.summary()` is rounded explicitly to two places:
  `(total / count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` - the same rule a
  bank uses for half-paisa.
- `PayrollService.parse_amount()` converts form input with `Decimal(str(raw).strip())` and
  rejects anything that is not a finite number.
- Display formatting is `f"{amount:,.2f}"` through the `money` template filter.

`Decimal` is slower than `float`, but payroll runs once a month - correctness matters far
more than speed here.

---

## 7. How salary calculations work

**Formulas implemented in `models/payroll.py`**

| Item | Formula |
| --- | --- |
| Gross salary | `basic_salary + hra + other_allowances` |
| Total deductions | `pf_deduction + professional_tax` |
| Net salary | `gross_salary - total_deductions` |

**Rules enforced**

- Every component must be `>= 0` (negative HRA or PF is rejected).
- `pf_deduction + professional_tax` may not exceed `gross_salary`, so net salary cannot
  become negative.
- The basic salary itself must be `> 0` (`Employee`).

**Worked example (uses the seeded record EMP001)**

| Component | Amount (Rs.) |
| --- | --- |
| Basic salary | 55,000.00 |
| HRA | 22,000.00 |
| Other allowances | 8,000.00 |
| **Gross salary** | **85,000.00** |
| PF | 6,600.00 |
| Professional tax | 200.00 |
| **Total deductions** | **6,800.00** |
| **Net salary** | **78,200.00** |

This is exactly what the payslip, the dashboard total and `data/payroll.csv` show - the
same object is used everywhere.

**Sequence when the user submits the payroll form**

1. `EmployeeService.search_employee(emp_id)` loads the employee (or returns `None`).
2. `PayrollService.parse_amount()` validates the four amounts.
3. `Payroll(...)` runs `__post_init__`, which validates and normalises.
4. The payslip template reads the three computed properties.
5. Saving appends the six stored values plus the three computed values to `payroll.csv`,
   so the historical record keeps what was actually paid.

---

## 8. How Pandas is used

`analytics/salary_analysis.py` uses Pandas to analyse the payroll ledger. Pandas is used
**for reporting only** - it never changes stored data.

```python
df = pd.read_csv(csv_manager.PAYROLL_FILE)      # payroll.csv -> DataFrame
```

| Operation | Code | Result |
| --- | --- | --- |
| Record count | `len(df)` | number of transactions |
| Total expenditure | `df["net_salary"].sum()` | sum of all net salaries |
| Average | `df["net_salary"].mean()` | mean net salary |
| Highest / lowest | `.max()` / `.min()` | extremes |
| Department totals | `df.groupby("department").agg(employees=("net_salary","size"), total=("net_salary","sum"), average=("net_salary","mean")).sort_values("total", ascending=False)` | one row per department, sorted by payout |

The results are returned as plain dictionaries/lists (`summary()`,
`department_summary()`) so templates can render them directly, and they are also printed
by the console version (`display_summary()`, `department_analysis()`).

Empty-data cases are handled: `load_data()` returns `None` for a missing file, an empty
file (`pd.errors.EmptyDataError`) or an empty table, and the analytics page then shows an
explanatory message instead of an error.

---

## 9. How Matplotlib is used

`analytics/charts.py` turns the same DataFrame into three images:

1. **Bar chart** - net salary of each employee (`plt.bar(df["name"], df["net_salary"])`).
2. **Pie chart** - share of total payout per department
   (`df.groupby("department")["net_salary"].sum()`).
3. **Histogram** - distribution of net salaries (`plt.hist(df["net_salary"], bins=5)`).

**Details**

- A `Figure` is built per request and drawn onto a `FigureCanvasAgg` (no `pyplot` global
  state), so several requests can render at the same time without interfering.
- The figure is saved into an in-memory buffer (`io.BytesIO`) and the bytes are returned
  from `/charts/<filename>` with `send_file(..., mimetype="image/png")`. **No file is
  written**, which is what makes the page work on Vercel's read-only filesystem.
- Rendered PNGs are cached in memory per data signature, so repeated page loads reuse the
  image until the payroll data changes.
- `generate_charts()` still writes the three PNG files into `charts/` - used by the console
  version and for offline copies - guarded by a `threading.Lock()`.
- If a chart cannot be drawn (no data, or a rendering error) the route returns a small
  placeholder PNG instead of a broken image or a stack trace, and the error is logged.
- The charts are **static images, not interactive plots** - a deliberate simplification.

---

## 10. How the website communicates with the backend

Two mechanisms are used, and only these two:

**a. Classic HTML form submission (used for every change)**

```
Browser form  --POST /payroll/new-->  Flask route  -->  service  -->  model
                                                                            |
Browser page  <--HTML rendered by Jinja2-------------------------------------
```

- The form uses `method="post"` and sends
  `application/x-www-form-urlencoded` data.
- Flask reads it with `request.form`, performs the work, and either re-renders the page
  (validation error, HTTP 400) or redirects to another URL (success, HTTP 302).
- The page the user sees is **rendered on the server**; the browser only receives HTML.
  There is no client-side state to lose, and the site works with JavaScript disabled
  (only the live preview panel needs it).

**b. One JSON endpoint for the live preview**

`templates/payroll_form.html` contains a small `fetch()` call:

```javascript
const response = await fetch("/api/calculate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload)
});
const data = await response.json();   // { ok, gross_salary, total_deductions, net_salary }
```

`api_calculate()` returns `jsonify({...})` on success, or
`jsonify({"ok": False, "error": message}), 400` when an amount is invalid. The JavaScript
only updates four text fields - **no salary arithmetic happens in the browser**, so the
figure shown in the panel is exactly what the server will save.

Messages such as "Payroll saved" reach the next page through Flask's flash mechanism
(signed cookie), not through JavaScript.

---

## 11. How validation and exception handling work

**Three defensive layers**

1. **The browser** marks required fields and sets numeric input types. This is convenience
   only - it can be bypassed, so it is never trusted.
2. **The model** refuses to build an invalid object (`Employee.__post_init__`,
   `Payroll.__post_init__`). This is the real guarantee: even a bug in a route cannot
   create an employee with an empty name or a payroll with a negative net salary.
3. **The routes and services** convert and check user text before it reaches the model
   (`PayrollService.parse_amount`), and catch `ValueError` to show a readable message.

**Validation rules**

| Field | Rule | Where |
| --- | --- | --- |
| Employee ID | required, unique | `Employee.__post_init__`, `CSVManager.save_employee` |
| Name / department / designation | required, trimmed | `Employee.__post_init__` |
| Basic salary | numeric, finite, > 0 | `Employee.__post_init__`, `parse_amount(..., allow_zero=False)` |
| HRA / allowances / PF / tax | numeric, finite, >= 0, required | `PayrollService.parse_amount` |
| Deductions | `pf + tax <= gross` | `Payroll.__post_init__` |
| Employee selection | must be an existing ID | routes (`search_employee` returns `None` -> error) |

**Error handling in each layer**

- **Model/service:** raise `ValueError` with a message written for the user
  ("Basic salary must be positive.").
- **Web routes:** `try: ... except ValueError as error: flash(str(error), "error")` and
  re-render the form with HTTP 400, keeping what the user typed.
- **Missing records:** `abort(404)`, rendered by `@app.errorhandler(404)` as a friendly
  page with navigation, not a stack trace.
- **Unexpected errors:** `@app.errorhandler(500)` renders a page telling the user to check
  the terminal; the traceback stays in the console log rather than the browser.
- **JSON endpoint:** returns `{"ok": false, "error": "..."}` with status 400 so the
  JavaScript can display the message inline.
- **Console version:** each menu action runs inside `try/except` and prints
  `Unexpected error: <type>: <message>`, then returns to the menu - the program never dies
  because of one bad entry. Numeric input uses a retry loop (`get_decimal_input`).

---

## 12. What tests were conducted

The suite is `tests/`, run with `python -m pytest tests/ -v`. **53 automated tests, all
passing** (verified on 15 November 2026, Python 3.14.7, pytest 9.2.0, `53 passed in 6.17s`;
the database tests also pass against a real PostgreSQL 18 database).

| File | Tests | Behaviour verified |
| --- | --- | --- |
| `test_employee.py` | 3 | Employee creation stores correct fields; empty name raises `ValueError`; negative salary raises `ValueError` |
| `test_payroll.py` | 5 | Gross = 40,000; deductions = 2,200; net = 37,800; negative allowance rejected; deductions greater than gross rejected |
| `test_csv.py` | 5 | Both CSV files created with correct headers; employee saved and loaded back; duplicate ID rejected; payroll row saved with correct gross/net; `replace_employees` rewrites the file |
| `test_web.py` | 22 | Dashboard renders; dashboard shows a saved payroll; add employee creates a record; duplicate ID rejected (400); empty name rejected (400); search filters; edit updates a salary; delete removes a record; unknown employee gives 404; payroll preview shows 40,000 / 37,800; preview does not save; save persists the record; negative amount rejected; history lists records; saved payslip page renders; JSON API returns 40,000 / 37,800; JSON API rejects `"abc"`; analytics page links the charts and writes no files; `/charts/*.png` returns `image/png`; unknown chart name gives 404; no-data and rendering-error cases return a placeholder PNG |
| `test_database.py` | 18 | Database repository CRUD, duplicate `emp_id` rejected, payroll save and history, history unchanged after an employee edit, history kept after an employee delete (foreign key cleared), Decimal exactness, persistence across a reconnect, unreachable database raises `StorageError`, backend selection, CSV migration import / repeatability / non-overwrite / invalid rows / dry run, and a full Flask workflow against the database store |

**How the tests stay safe**

- `test_csv.py` and `test_web.py` use pytest's `tmp_path` and `monkeypatch` to point
  `csv_manager.DATA_DIR`, `EMPLOYEE_FILE` and `PAYROLL_FILE` (and `charts.CHART_DIR`) at a
  temporary folder. The real `data/` and `charts/` files are never touched - this is also
  why `salary_analysis.py` and `charts.py` reference `csv_manager.PAYROLL_FILE` at call
  time instead of copying the value once at import.
- `test_web.py` uses Flask's `test_client()`, which sends requests straight to the
  application without starting a server or opening a browser.

**Manual checks performed**

- Started the server (`python app.py`) and requested every page: `/`, `/employees`,
  `/employees/add`, `/payroll/new`, `/payroll`, `/analytics` returned HTTP 200;
  `/api/calculate` returned 405 for GET (POST only); an unknown URL returned the custom
  404 page; `static/css/style.css` loaded with status 200 and no console errors.
- Confirmed the live calculation in the browser: basic 32,000 + HRA 25,000 + allowances
  10,000 = gross 67,000; deductions 7,200; net 59,800.
- Confirmed the console version starts, shows the menu and exits cleanly.
- Not tested: concurrent users, deployment on a remote server, and behaviour under a
  different browser. The development server is not a production environment.
