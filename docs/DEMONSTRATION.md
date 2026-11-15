# Live Demonstration Script

**Employee Payroll Management System** - 5 to 8 minutes, single laptop.

---

## Before you start (5 minutes earlier, not counted)

1. Open a terminal in the project folder and activate the environment:

   ```bash
   .venv\Scripts\activate          # Windows
   source .venv/Scripts/activate   # Git Bash
   ```

2. Restore a clean dataset:

   ```bash
   python scripts/reset_data.py --demo
   ```

   Expected: `employees: 6`, `payroll: 5`.

3. Start the server:

   ```bash
   python app.py
   ```

   Wait for `Running on http://127.0.0.1:5000`, then open that address in the browser.
   Keep the terminal visible - it shows every request, which is useful while explaining.

4. Have the folder open in a file browser as well, so `data/payroll.csv` can be shown.

**Numbers you will use in the demo** (so nothing is calculated live under pressure):

| Field | Value |
| --- | --- |
| Employee | EMP006 - Neha Kulkarni (basic 32,000) |
| HRA | 25,000 |
| Other allowances | 10,000 |
| PF | 7,000 |
| Professional tax | 200 |
| Expected gross | **67,000** |
| Expected net | **59,800** |

---

## Step 1 - Open the website (0:00 - 0:20)

*Action:* browser is already on `http://127.0.0.1:5000`.

*Say:*

> This is the Employee Payroll Management System. It is a Python mini project built with
> Flask for the web interface, object-oriented programming for the payroll logic, CSV
> files for storage, and Pandas and Matplotlib for analytics. It is running locally on
> this laptop on port 5000 - no internet is needed.

---

## Step 2 - Explain the dashboard (0:20 - 1:00)

*Action:* point at each stat card, then the two panels, then the bottom chip.

*Say:*

> The dashboard is the summary screen. Four cards show the number of employees, the number
> of payroll transactions, the total net payout across all transactions, and the average
> net salary.
>
> Below that, the left panel lists the five most recent payroll transactions with their
> gross and net salary, and each row links to its payslip. The right panel shows
> department-wise payouts as bars - the longest bar is Operations at 85,600 rupees.
>
> The yellow notice says this is sample demonstration data. It is not real payroll; it is
> labelling provided so the records are never mistaken for real data.
>
> This whole page is computed from two CSV files: employees.csv and payroll.csv.

---

## Step 3 - Add a new employee (1:00 - 1:50)

*Action:* click **+ Add Employee**. Type:

| Field | Value |
| --- | --- |
| Employee ID | EMP007 |
| Name | Meera Iyer |
| Department | Information Technology |
| Designation | QA Engineer |
| Basic salary | 36000 |

*Say (while typing):*

> The employee ID must be unique - the storage layer checks the file before writing.
> Every field is required, and the basic salary must be positive.

*Action:* click **Add employee**. The list reloads with the new row and a green message
appears.

*Say:*

> The success message is a Flask flash message. Behind the scenes the form was posted to
> a Flask route, the route built an Employee object, the object's validation ran, and one
> line was appended to employees.csv. The page you see was rendered on the server with
> Jinja2.

---

## Step 4 - Search and edit an employee (1:50 - 2:40)

*Action:* in the search box type `meera` and press **Search**.

*Say:*

> Search works on ID, name, department and designation, and is case-insensitive. It is a
> normal GET request with `?q=meera`, handled by the same route that lists employees.

*Action:* click **Edit** on Meera Iyer. Change Designation to `QA Engineer` ->
`Senior QA Engineer` and basic salary to `40000`. Click **Save changes**.

*Say:*

> On edit, the employee ID is read-only - it is the key that payroll records use. Notice
> the form was pre-filled with the current values.
>
> Updating is more expensive than adding: CSV cannot change a row in place, so the service
> loads all employees, replaces this one, and rewrites the file once. That logic lives in
> `replace_employees()` in the storage layer.

---

## Step 5 - Process a payroll transaction (2:40 - 3:40)

*Action:* click **Process Payroll** in the navigation. Select
**EMP006 - Neha Kulkarni**. Enter HRA `25000`, Other allowances `10000`,
PF `7000`, Professional tax `200`.

*Say (after the last field):*

> Watch the right-hand panel. Every time an amount changes, the page sends a small JSON
> request to `/api/calculate`, and the Python backend returns the calculated gross,
> deductions and net salary. The arithmetic is not done in JavaScript - it is done by the
> same Payroll class that will save the record, so the previewed figure cannot differ from
> the saved figure.

---

## Step 6 - Show the salary calculation (3:40 - 4:30)

*Action:* point at the four lines of the live panel, then at the form labels.

*Say:*

> The formulas are simple but must be exact:
>
> - Gross salary = basic + HRA + other allowances = 32,000 + 25,000 + 10,000 = 67,000.
> - Total deductions = PF + professional tax = 7,000 + 200 = 7,200.
> - Net salary = gross - deductions = 67,000 - 7,200 = 59,800.
>
> These three values are Python **properties** on the Payroll class - they are computed
> from the components every time they are read, so they can never go out of date.
>
> All money is handled with Python's Decimal type, not float. Float is binary and produces
> results like 0.1 + 0.2 = 0.30000000000000004; for salaries that would be a wrong paisa
> amount. Decimal works in base ten, so 59,800.00 is exactly 59,800.00.

---

## Step 7 - Open the generated payslip (4:30 - 5:10)

*Action:* click **Calculate & preview payslip**.

*Say:*

> This is the payslip. Earnings on the left, deductions on the right, and the net salary
> payable highlighted at the bottom. It is generated from the Payroll object in memory.
>
> Important: nothing has been saved yet. A payroll transaction is a financial record, so
> the system always shows the payslip first and saves only when you confirm.
>
> The Print button prints this page using a print stylesheet that hides the navigation -
> it can also be saved as a PDF from the browser's print dialog.

*Action:* click **Save payroll record**.

*Say:*

> Now one row has been appended to payroll.csv, and I was redirected to the history page
> with a confirmation message.

---

## Step 8 - Show payroll history (5:10 - 5:40)

*Action:* the browser is now on **Payroll History**. Point at the totals, then the rows.

*Say:*

> Six transactions now, the newest first, with basic, gross, deductions and net salary.
> The three cards at the top are recalculated from the file every time the page loads.
>
> Each row stores a snapshot of the employee's name, department and basic salary at the
> time of processing - so if the employee is later edited or deleted, the historical
> record still shows what was actually paid.

*Action:* click **Payslip** on the newest row, then **Back to history**.

*Say:*

> A saved payslip can be reopened at any time from the stored record.

---

## Step 9 - Open analytics and charts (5:40 - 6:40)

*Action:* click **Analytics**.

*Say:*

> This page is the reporting layer. Pandas reads payroll.csv into a DataFrame and
> calculates the record count, total expenditure, average, highest and lowest net salary,
> plus the department table below - department, number of employees, total paid and
> average. Grouping is a single `groupby("department")` with an aggregation, sorted by
> total payout.
>
> The three charts are produced by Matplotlib and saved as PNG files in the charts folder:
> a bar chart comparing each employee's net salary, a pie chart of department-wise payroll
> share, and a histogram of the salary distribution.
>
> The charts are regenerated automatically when payroll.csv changes - the code compares
> file timestamps - so after the payroll I just saved, the new employee is already included
> in the bar chart.

*Action:* click **Regenerate charts** to show the explicit refresh.

---

## Step 10 - Explain the architecture and Python implementation (6:40 - 8:00)

*Action:* switch to the editor / folder view.

*Say:*

> The project is layered, and both front ends share the same core.
>
> - `models/` holds the Employee and Payroll classes. They are dataclasses, and
>   `__post_init__` validates every object - an employee with an empty name or a negative
>   salary cannot be created at all. That is encapsulation.
> - `Payroll` contains an Employee object, which is composition, and exposes gross,
>   deductions and net as properties.
> - `services/` holds the business rules: employee add/search/update/delete, amount
>   parsing, summaries.
> - `storage/csv_manager.py` is the only file that touches CSV - append for new records,
>   full rewrite for edits and deletes.
> - `analytics/` holds the Pandas analysis and the Matplotlib charts.
> - `app.py` is the Flask web layer: routes, templates, validation messages, and one JSON
>   endpoint for the live calculation.
> - `main.py` is a console version with the same ten operations, reusing the same services.
>
> The web layer contains no salary arithmetic - it only validates input, calls the service
> layer and chooses a template. That is why the website and the terminal produce identical
> numbers.
>
> The whole project is covered by 53 automated tests written with pytest - model
> validation, salary calculations, CSV persistence, and every web route - and all of them
> pass.

---

## Closing line

> So the system manages employees, calculates and stores payroll exactly, produces
> payslips, keeps permanent history and reports analytics - running entirely locally from
> two CSV files.

---

## If something goes wrong

| Problem | Fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'flask'` | The virtual environment is not active. Run `python -m pytest` / `app.py` with `.venv\Scripts\activate` first |
| `Address already in use` on port 5000 | An old server is still running: press `CTRL+C` in that terminal, or run on another port with `flask --app app run --port 5001` |
| Data looks wrong after practice runs | `python scripts/reset_data.py --demo` and reload the page |
| Charts look outdated | Click **Regenerate charts** on the Analytics page |
| Browser shows a stale page | Press `CTRL+F5` |

## Timing summary

| Step | Activity | Time |
| --- | --- | --- |
| 1 | Open the website | 0:20 |
| 2 | Dashboard | 0:40 |
| 3 | Add employee | 0:50 |
| 4 | Search and edit | 0:50 |
| 5 | Process payroll | 1:00 |
| 6 | Salary calculation | 0:50 |
| 7 | Payslip | 0:40 |
| 8 | Payroll history | 0:30 |
| 9 | Analytics and charts | 1:00 |
| 10 | Architecture | 1:20 |
| | **Total** | **~7:00** |
