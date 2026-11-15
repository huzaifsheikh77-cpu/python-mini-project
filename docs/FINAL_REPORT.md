# Final Implementation Report

**Project:** Employee Payroll Management System
**Type:** Python mini project (third semester B.Tech)
**Team:** Sheikh Huzaifa (25BTRCP048), Pradhyot Tiple (25BTRCP037), Akshat Tiwari (25BTRCP002)
**Report date:** 15 November 2026
**Environment verified on:** Windows 11, Python 3.14.7, pytest 9.2.0

---

## 1. Project summary

The Employee Payroll Management System is a locally hosted web application that manages
employee records and payroll transactions for a small organisation. Employees are stored
with an ID, name, department, designation and basic salary. A payroll transaction records
HRA, other allowances, PF and professional tax, and derives gross salary, total deductions
and net salary using `decimal.Decimal` arithmetic.

The application provides a dashboard, an employee directory with search/add/edit/delete, a
payroll processing screen with a live server-side calculation, a printable payslip, a
permanent payroll history, and salary analytics built with Pandas and Matplotlib. A console
version (`main.py`) exposes the same ten operations using the same model, service and
storage code.

All data is kept in two CSV files inside `data/`; no database or hidden configuration is
required. The solution runs with one command on a laptop with no internet connection.

---

## 2. Implemented features

### Web application (`app.py` + `templates/`)

| Feature | Status | Evidence |
| --- | --- | --- |
| Dashboard with headcount, transaction count, total payout, average salary | Working | `/`, `templates/index.html`, screenshot 01 |
| Recent payroll table with per-record payslip links | Working | `/` |
| Department payout bars | Working | `/`, `PayrollService.department_totals()` |
| "Employees waiting for payroll" panel | Working | `/` |
| Sample-data notice on the dashboard | Working | `data/DEMO_DATA.txt` marker |
| Employee list | Working | `/employees`, screenshot 02 |
| Search by ID / name / department / designation | Working | `/employees?q=`, test `test_employee_search_filters_results` |
| Add employee with validation | Working | `/employees/add`, tests |
| Edit employee (ID read-only) | Working | `/employees/<id>/edit`, test |
| Delete employee with confirmation, history preserved | Working | `/employees/<id>/delete`, test |
| Payroll form with component inputs | Working | `/payroll/new`, screenshot 03 |
| Live salary calculation by the Python backend | Working | `POST /api/calculate`, verified in browser ({32,000 + 25,000 + 10,000} -> gross 67,000, net 59,800) |
| Payslip preview before saving | Working | `templates/payslip.html`, screenshot 04 |
| Save payroll record only after confirmation | Working | `POST /payroll/save`, test `test_payroll_preview_is_not_saved_until_confirmed` |
| Printable payslip (print stylesheet) | Working | `Print` button, `@media print` in `style.css` |
| Payroll history, newest first, with totals | Working | `/payroll`, screenshot 05 |
| Re-open any saved payslip | Working | `/payroll/<index>`, test |
| Analytics summary + department table | Working | `/analytics`, screenshot 06 |
| Three Matplotlib charts, auto-regenerated on data change | Working | `analytics/charts.py`, test `test_analytics_page_generates_charts` |
| Custom 404 and 500 pages | Working | `templates/error.html`, tested for 404 |
| Responsive layout (desktop and narrow screens) | Working | `static/css/style.css` media queries; checked at 1400 px and 430 px |
| Offline operation (no CDN, no external assets) | Working | all CSS/JS local |

### Console application (`main.py`)

| Feature | Status |
| --- | --- |
| Menu with 10 operations (add, view, search, update, delete, process payroll, history, analytics, charts, exit) | Working |
| Decimal input validation with retry loop | Working |
| Payslip printed to the terminal | Working |
| Verified start and clean exit | Yes (menu displayed, exit message, exit code 0) |

### Tooling

| Item | Status |
| --- | --- |
| `requirements.txt` with pinned versions, verified in a fresh virtual environment | Working |
| `scripts/reset_data.py --demo` / `--empty` | Working |
| Automated test suite (53 tests) | All passing |
| Documentation set (README + 4 documents + screenshots) | Complete |

---

## 3. Technology stack

| Layer | Technology | Version |
| --- | --- | --- |
| Language | Python | 3.14.7 |
| Web framework | Flask | 3.1.3 |
| WSGI server (development) | Werkzeug | 3.1.9 |
| Templates | Jinja2 | 3.1.6 |
| Data analysis | Pandas | 3.1.1 |
| Charts | Matplotlib | 3.11.2 |
| Numerics | NumPy | 2.5.4 |
| Storage | CSV (`csv` module) | standard library |
| Money arithmetic | `decimal.Decimal` | standard library |
| Testing | pytest | 9.2.0 |
| Front end | HTML5, CSS3, vanilla JavaScript | - |

---

## 4. Architecture

```
Browser (HTML forms + one fetch() call)
   |
   v
app.py ............ Flask routes, validation feedback, templates, JSON endpoint
   |
   v
services/ ......... EmployeeService (CRUD rules), PayrollService (parsing, building,
   |                 history, summaries)
   v
models/ ........... Employee (validated dataclass), Payroll (composition + computed
   |                 properties gross_salary / total_deductions / net_salary)
   v
storage/ .......... CSVManager - the only module that touches data/*.csv
   |
   +--> analytics/ . SalaryAnalysis (Pandas), PayrollCharts (Matplotlib PNGs)

main.py ........... console front end using the same services
```

Key design decisions:

- **One core, two front ends.** No salary arithmetic exists in a route or a template.
- **Validation inside the model.** `__post_init__` makes invalid objects impossible.
- **Single storage gateway.** All file access is in `CSVManager`.
- **Decimal everywhere money is calculated**, converted at every boundary with
  `Decimal(str(value))`.
- **Preview without side effects.** The payslip is rendered from memory; only an explicit
  confirmation appends the row.

---

## 5. Important files

| File | Responsibility | Lines (approx.) |
| --- | --- | --- |
| `app.py` | Flask application: 13 routes, template filter, error handlers, entry point | 480 |
| `main.py` | Console menu with 10 operations | 300 |
| `models/employee.py` | `Employee` dataclass, validation, `display_details()` | 45 |
| `models/payroll.py` | `Payroll` dataclass, three computed properties, `generate_payslip()` | 70 |
| `services/employee_service.py` | Add, search, update, delete employees | 65 |
| `services/payroll_service.py` | Amount parsing, payroll construction, history, summaries | 145 |
| `storage/csv_manager.py` | File initialisation, append, load, rewrite | 130 |
| `analytics/salary_analysis.py` | Pandas loading and summaries (overall + department) | 115 |
| `analytics/charts.py` | Matplotlib charts, staleness check, thread lock | 130 |
| `templates/` | 9 Jinja2 templates (layout, dashboard, employees, forms, payslip, history, analytics, error) | - |
| `static/css/style.css` | Responsive layout, print styles | ~700 |
| `scripts/reset_data.py` | Sample dataset restore / clear | 135 |
| `tests/test_*.py` | 53 automated tests | 545 |
| `data/employees.csv` | Employee master data | seeded |
| `data/payroll.csv` | Payroll ledger | seeded |
| `requirements.txt` | Pinned dependencies | 20 |

---

## 6. Testing results

**Command used**

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```

**Actual output (15 November 2026)**

```
platform win32 -- Python 3.14.7, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\PYTHON MINI PROJECT
collected 53 items
...
53 passed in 6.17s
```

### Actual test counts

| Test file | Tests | Result |
| --- | --- | --- |
| `tests/test_employee.py` | 3 | 3 passed |
| `tests/test_payroll.py` | 5 | 5 passed |
| `tests/test_csv.py` | 5 | 5 passed |
| `tests/test_web.py` | 22 | 22 passed |
| `tests/test_database.py` | 18 | 18 passed (also re-run against real PostgreSQL 18) |
| **Total** | **53** | **53 passed, 0 failed, 0 skipped** |

During this final preparation pass the suite found one real defect: `CSVManager.load_employees()`
converted `basic_salary` through `float`, so a reloaded employee lost Decimal exactness and
the JSON API returned `40000.0` instead of `40000`. The conversion was changed to pass the
CSV string straight into `Employee` (which converts with `Decimal(str(...))`), and all 31
tests then passed. The suite now holds 53 tests: the original 31, 18 Supabase database
tests and 4 chart-response tests added when charts moved from disk files to in-memory
streaming.

### Other verification performed

| Check | Result |
| --- | --- |
| Fresh virtual environment + `pip install -r requirements.txt` | Passed - no missing dependency |
| `python app.py` starts and answers on `http://127.0.0.1:5000` | Passed |
| `GET /`, `/employees`, `/employees/add`, `/payroll/new`, `/payroll`, `/analytics` | 200 for all |
| `GET /api/calculate` | 405 (POST-only endpoint, as designed) |
| `GET /nope` | 404 custom page |
| `static/css/style.css` | 200, no console errors on any visited page |
| Live calculation in the browser | basic 32,000 + HRA 25,000 + allowances 10,000 = 67,000; deductions 7,200; net 59,800 - correct |
| Payslip preview then save then history | Correct values, one row appended |
| Analytics page | Renders 3 charts from the current data |
| `python main.py` console version | Menu displayed, exited cleanly with code 0 |
| Sample data reset | 6 employees, 5 payroll records restored |

### Not tested (stated honestly)

- Concurrent access by two users saving at the same time (not supported by design).
- Deployment on a public server, HTTPS or a production WSGI server.
- Browsers other than the Chromium-based browser used for the screenshots.
- Mobile behaviour beyond one narrow-width (430 px) visual check.
- Load or performance testing of any kind.

No security certification, penetration test or deployment claim is made anywhere in this
project.

---

## 7. Screenshots

Captured from the running application on 15 November 2026 and stored in
`docs/screenshots/`.

| File | Page | Shows |
| --- | --- | --- |
| `01-dashboard.png` | `/` | Stat cards, recent payroll, department payouts, sample-data notice |
| `02-employees.png` | `/employees` | Employee directory, search bar, edit/delete actions |
| `03-process-payroll.png` | `/payroll/new` | Payroll form and the live calculation panel |
| `04-payslip.png` | payslip preview | Earnings, deductions, net salary, save confirmation |
| `05-payroll-history.png` | `/payroll` | Five transactions with totals |
| `06-analytics.png` | `/analytics` | Summary cards, department table, three charts |
| `07-mobile.png` | `/employees` at 430 px | Narrow-screen layout |

**To recapture them yourself**

1. `python app.py`
2. Open `http://127.0.0.1:5000` in a browser.
3. For each page in the table above, press `F11` for full screen if you want no browser
   chrome, then use the browser's screenshot or `Win + Shift + S`, and save the file into
   `docs/screenshots/` using the same names.

---

## 8. Known limitations

1. No authentication, authorisation or user accounts - anyone with the address can use it.
2. CSV storage has no locking or transactions; concurrent writers can lose data.
3. Payroll records have no pay-period (month/date) column, so repeated runs for the same
   employee look identical in the history.
4. Payslips are HTML pages with a print stylesheet; there is no PDF generation or e-mail.
5. HRA, PF and tax are entered manually instead of being derived from salary percentages.
6. The Flask development server with `debug=True` is used; this is not a production
   configuration.
7. Editing an employee overwrites the old values - there is no audit trail.
8. Charts are static PNG images, not interactive.
9. No class inheritance; OOP is shown through classes, encapsulation, composition and
   properties.
10. Data volumes are limited to the low thousands of rows before CSV becomes impractical.
11. Deleting an employee keeps their payroll history by design, so a deleted employee can
    still appear in older payroll records.

---

## 9. Run instructions

```bash
# 1. Project folder
cd "PYTHON MINI PROJECT"

# 2. Virtual environment (once)
python -m venv .venv
.venv\Scripts\activate            # Windows; Git Bash: source .venv/Scripts/activate

# 3. Dependencies
python -m pip install -r requirements.txt

# 4. Sample data (optional, restores the demonstration dataset)
python scripts/reset_data.py --demo

# 5. Start the website
python app.py
#    -> open http://127.0.0.1:5000

# 6. Console version instead
python main.py

# 7. Tests
python -m pytest tests/ -v        # 53 passed
```

Stop the web server with `CTRL+C`.

---

## 10. Final project status

| Acceptance criterion | Verified | Notes |
| --- | --- | --- |
| Website runs locally | Yes | `python app.py`, served on 127.0.0.1:5000, all pages return 200 |
| Complete employee management (add, view, search, edit, delete) | Yes | All five operations verified by tests and in the browser |
| Payroll processing works end to end | Yes | Preview, confirmation, save, history, payslip |
| Salary calculations are correct | Yes | Hand-checked (32,000 + 25,000 + 10,000 -> 67,000 gross, 59,800 net) and unit-tested |
| Records are preserved | Yes | Verified in `data/payroll.csv`; history reloads after restart |
| Payroll history is displayed | Yes | Newest first, with totals and per-record payslips |
| Meaningful analytics | Yes | Pandas summary, department table, 3 Matplotlib charts regenerated from current data |
| Professional, responsive interface | Yes, with the caveat that only two viewport widths were inspected visually | Consistent design, local CSS, media queries, print styles |
| Documented run and test commands | Yes | README verified against the real commands |
| No dependency on hidden local configuration | Yes | Only optional `PAYROLL_SECRET_KEY` override; everything else defaults |
| Sample data clearly identified and resettable | Yes | Dashboard notice, `data/DEMO_DATA.txt`, `scripts/reset_data.py` |
| Tests pass | Yes | 53 passed, 0 failed |

### Note on the state of the repository at the start of this pass

When this final preparation pass began, the repository contained the console application
only: `main.py`, the models, services, storage and analytics modules, and 13 pytest tests.
There was no Flask application, no `templates/` or `static/` directory, Flask was not in
`requirements.txt`, and three of the files in `tests/` were manual scripts that ran on
import and appended duplicate rows to `data/payroll.csv` (the source of the duplicated
records that were cleared).

To deliver the website required by the project scope, the Flask layer (`app.py`, 9
templates, stylesheet, JSON calculation endpoint, payslip page), `services/payroll_service.py`,
the demo-data reset script and 18 web tests were implemented in this pass, and the three
manual scripts plus the temporary `check_payroll.py` debugging file were removed so that
`pytest tests/` now runs only real tests and never mutates project data. All claims in this
report were verified after those changes.

---

## 11. Verdict

# READY FOR DEMONSTRATION

The application runs locally with one command, supports complete employee management and
payroll processing, produces correct salary calculations and printable payslips, preserves
records in CSV files, shows payroll history, provides meaningful Pandas/Matplotlib analytics,
and has a consistent responsive interface. All 53 automated tests pass and every page was
inspected in a running browser.

The documented limitations - no authentication, single-user CSV storage, no pay-period
column, no PDF payslips, and use of Flask's development server - are scope decisions for an
academic mini project rather than defects, and each is listed in the README. Nothing in this
project has been deployed, and no security certification or production-readiness claim is
made.
