# Supabase PostgreSQL Integration - Implementation Report

**Project:** Employee Payroll Management System
**Scope:** persistent database storage for employees and payroll records
**Date:** 15 November 2026
**Status:** implemented and verified against a real PostgreSQL 18 engine;
**not yet connected to a live Supabase project** (no credentials were supplied, see
[section 9](#9-what-was-not-verified))

---

## 1. Summary

The application previously persisted everything in two CSV files. It now uses
**Supabase PostgreSQL** as its persistent database through a repository layer, while the
CSV backend remains available for offline use, demos and import/export.

What was added:

| Area | Deliverable |
| --- | --- |
| Schema | `migrations/001_init_schema.sql` (tables, keys, constraints, indexes, trigger, RLS) |
| Repository | `storage/database_store.py` - all SQL, no queries in routes |
| Configuration | `storage/database.py` (env loading, URL normalisation, engine factory) |
| Backend switch | `storage/backend.py` (`PAYROLL_STORAGE`, graceful CSV fallback) |
| Migration | `storage/migration.py` + `scripts/migrate_csv_to_supabase.py` |
| Schema tooling | `scripts/init_db.py` |
| CSV export | `scripts/export_db_to_csv.py` |
| Environment | `.env.example` (placeholders only), `.env` git-ignored |
| Tests | `tests/test_database.py` (18 new tests) + `tests/conftest.py` safety guard |
| Dependencies | `sqlalchemy==2.1.8`, `psycopg[binary]==3.3.9`, `python-dotenv==1.2.4` |

Nothing about the UI, colours, templates, forms, employee fields or payroll formulas
changed. The project is still called **Employee Payroll Management System** everywhere.
No Vercel deployment was performed.

---

## 2. Existing data flow (inspected before changing anything)

```
templates/  --form POST--> app.py (routes) --> services/* --> storage/csv_manager.py --> data/*.csv
                                                   |
                                        analytics/salary_analysis.py (pandas.read_csv)
                                                   |
                                        analytics/charts.py (matplotlib -> PNG in memory)

main.py (console) ----------> services/* --> storage/csv_manager.py
```

Findings that shaped the design:

- `app.py` routes contained no salary arithmetic: they validate input, call
  `EmployeeService` / `PayrollService`, and render templates.
- `CSVManager` was the single storage gateway, but `services/` imported it directly, so
  swapping storage meant introducing an indirection point.
- `analytics/salary_analysis.py` read `payroll.csv` with `pd.read_csv`, i.e. it depended on
  the CSV file rather than on a records source.
- `analytics/charts.py` decided staleness from the `payroll.csv` modification time.
- Existing tests (`tests/test_csv.py`, `tests/test_web.py`) monkeypatch
  `csv_manager.EMPLOYEE_FILE` / `PAYROLL_FILE` to temporary paths.
- The CSV data at inspection time held **7 employees** and **6 payroll records**,
  including `EMP007 Huzaifa / IT / SE`, all legitimate and preserved.

---

## 3. Database architecture

The schema is `migrations/001_init_schema.sql` (idempotent; run it in the Supabase SQL
editor or with `python scripts/init_db.py`).

### `employees` - current master data

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGSERIAL` | primary key |
| `emp_id` | `VARCHAR(40)` | **UNIQUE**, not blank |
| `name` | `VARCHAR(120)` | not blank |
| `department` | `VARCHAR(80)` | not blank, indexed |
| `designation` | `VARCHAR(80)` | not blank |
| `basic_salary` | `NUMERIC(14,2)` | `> 0` |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT now()` |
| `updated_at` | `TIMESTAMPTZ` | maintained by trigger `employees_set_updated_at` |

Indexes: `employees_department_idx`, `employees_name_idx` (`lower(name)`).

### `payroll_records` - one row per processed payroll transaction

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGSERIAL` | primary key |
| `employee_id` | `BIGINT` | FK -> `employees(id)` **ON DELETE SET NULL**, indexed |
| `emp_id` | `VARCHAR(40)` | snapshot, indexed |
| `name`, `department` | `VARCHAR` | snapshot |
| `basic_salary`, `hra`, `other_allowances`, `pf_deduction`, `professional_tax` | `NUMERIC(14,2)` | components, `>= 0` (basic `> 0`) |
| `gross_salary`, `total_deductions`, `net_salary` | `NUMERIC(14,2)` | stored totals, `>= 0` |
| `source_ref` | `VARCHAR(120)` | nullable, **UNIQUE** - import bookkeeping |
| `processed_at` | `TIMESTAMPTZ` | `DEFAULT now()`, indexed descending |

Integrity constraints beyond `NOT NULL`:

```sql
CHECK (gross_salary = basic_salary + hra + other_allowances)
CHECK (net_salary  = gross_salary - total_deductions)
CHECK (basic_salary > 0), CHECK (hra >= 0), ... (each component)
```

**Historical accuracy.** A payroll row stores the employee's name, department and basic
salary *at processing time*. The foreign key is nullable and `ON DELETE SET NULL`, so:

- editing an employee does **not** change old payslips,
- deleting an employee clears the link but keeps the financial record,
- the payslip, history page and analytics keep working from the snapshot.

Both behaviours are covered by tests and were also reproduced directly in PostgreSQL
(section 7).

**Duplicate-import prevention.** `source_ref` is a deterministic SHA-1 of the source CSV
line (`emp_id|name|department|basic|hra|allowances|pf|tax`). A unique index makes a second
import of the same line a no-op. Application-created records leave `source_ref` NULL
(many NULLs are allowed by a unique index).

**Row level security** is enabled on both tables with no public policies, so the tables are
not exposed through Supabase's anon key; the Flask app connects with the database
credentials from `DATABASE_URL`.

---

## 4. Storage architecture

```
app.py routes ── EmployeeService / PayrollService ── get_store()
                                                      │
                             ┌────────────────────────┴─────────────────────┐
                             │                                              │
                   DatabaseStore (PostgreSQL)                    CSVManager (CSV files)
                   storage/database_store.py                     storage/csv_manager.py
```

- `storage/backend.py` resolves the backend once per process:
  `PAYROLL_STORAGE=csv` → CSV; `PAYROLL_STORAGE=database` → PostgreSQL; unset → PostgreSQL
  when `DATABASE_URL` exists, otherwise CSV.
- Both backends expose the same operations: `save_employee`, `import_employee_row`,
  `load_employees`, `update_employee`, `delete_employee`, `save_payroll`,
  `import_payroll_row`, `load_payroll_records`, `replace_employees`,
  `existing_source_refs`, `data_signature`, `initialize_files`.
- **No SQL in routes.** `app.py` calls `get_store().save_payroll(payroll)`; the only SQL in
  the project is inside `storage/database_store.py` (SQLAlchemy Core) and the migration file.
- **Decimal-safe.** Amounts are converted with `Decimal(str(value))` and rounded once to two
  places (`ROUND_HALF_UP`) before writing; `NUMERIC(14,2)` returns `Decimal`, and payroll
  history is handed back to the service layer as `Decimal` values.
  Derived totals are computed from the rounded components so a row always satisfies the
  database consistency checks.
- **Analytics** now builds its DataFrame from `get_store().load_payroll_records()` (money
  cast to `float` for charting only), so it works for either backend without reading a file.
- **Chart refresh** uses the store's `data_signature()` (`db:count:max_id:max_processed_at`
  or `csv:size:mtime`) instead of a CSV timestamp, and caches the rendered PNG in memory.
  Web requests never write a file - see `docs/DEPLOYMENT_READINESS.md`.
- **CSV import/export kept.** The CSV backend is unchanged for local runs;
  `scripts/export_db_to_csv.py` writes the database back out in the same column format.

---

## 5. Environment configuration

`.env.example` (committed) contains placeholders only:

```dotenv
PAYROLL_STORAGE=database
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require
# PAYROLL_TEST_DATABASE_URL=...   (tests only)
PAYROLL_SECRET_KEY=replace-with-a-long-random-string
```

- `.env` is listed in `.gitignore`; no credential, password or connection string is
  committed or printed by any script.
- `storage/database.py` loads `.env` with `python-dotenv` (`override=False`, so real
  environment variables always win) and normalises `postgres://` / `postgresql://` to the
  `postgresql+psycopg://` driver URL.
- **Serverless (Vercel):** use Supabase's **transaction pooler on port 6543** with
  `sslmode=require`. The engine is created with `NullPool` + `pool_pre_ping=True`, so no
  database connection is held between invocations and broken pooled connections are
  discarded before use. `DATABASE_URL` and `PAYROLL_SECRET_KEY` belong in the Vercel
  project's Environment Variables, not in the repository.
- Local/offline runs: `PAYROLL_STORAGE=csv` keeps the app fully functional without a
  database.

---

## 6. CSV migration

`python scripts/migrate_csv_to_supabase.py [--dry-run] [--no-backup]`

Sequence:

1. **Backup first** - `data/backups/<UTC timestamp>/` receives `employees.csv`,
   `payroll.csv` and `DEMO_DATA.txt` (`shutil.copy2`), before any row is read.
2. **Validate** every row through the `Employee` / `Payroll` models; validation failures are
   logged and skipped, never silently coerced.
3. **Employees**: insert only if `emp_id` is absent (`INSERT ... ON CONFLICT (emp_id) DO
   NOTHING`). Existing rows are never updated.
4. **Payroll**: insert with the deterministic `source_ref`
   (`ON CONFLICT (source_ref) DO NOTHING`); stored totals are recalculated from the
   components and any difference is logged as a warning.
5. **Log** every action (`INSERT` / `KEEP` / `SKIP` / `WARN` / `NOTE`) to
   `logs/migration_<UTC timestamp>.log`, and print a summary with counts.
6. **Exit codes**: `0` success, `1` completed with rejected rows, `2` configuration problem.

Payroll rows whose employee no longer exists are still imported as snapshots (designation
`Not recorded`), because they are financial history.

### Actual run against the real CSV files (2026-11-15)

Dry run:

```
DRY RUN - Employees: 7 imported, 0 already present, 0 invalid (of 7 CSV rows)
DRY RUN - Payroll:   6 imported, 0 already present, 0 invalid (of 6 CSV rows)
Database currently holds 0 employees and 0 payroll records (unchanged).
```

First real run:

```
Backup written to D:\PYTHON MINI PROJECT\data\backups\20261115T103433Z

Employees: 7 imported, 0 already present, 0 invalid (of 7 CSV rows)
Payroll:   6 imported, 0 already present, 0 invalid (of 6 CSV rows)
Database now holds 7 employees and 6 payroll records.
```

Second run (idempotency):

```
Employees: 0 imported, 7 already present, 0 invalid (of 7 CSV rows)
Payroll:   0 imported, 6 already present, 0 invalid (of 6 CSV rows)
Database now holds 7 employees and 6 payroll records.
```

After deliberately deleting employee `EMP001` directly in PostgreSQL and re-running:
`Employees: 1 imported, 6 already present` / `Payroll: 0 imported, 6 already present` -
the deleted employee came back, no payroll row was duplicated.

---

## 7. Verification

### Automated tests

| Suite | SQLite (default) | PostgreSQL 18 (real engine) |
| --- | --- | --- |
| `tests/test_employee.py` (3) | pass | pass |
| `tests/test_payroll.py` (5) | pass | pass |
| `tests/test_csv.py` (5) | pass | pass |
| `tests/test_web.py` (18) | pass | pass |
| `tests/test_database.py` (18) | pass | pass |
| **Total** | **53 passed** | **53 passed** |

The original 31 tests are unchanged and still pass. `tests/conftest.py` pins the suite to the
CSV backend and removes `DATABASE_URL` unless `PAYROLL_TEST_DATABASE_URL` is set, so a test
run can never write to a real Supabase project. Database tests truncate only the database
named in `PAYROLL_TEST_DATABASE_URL`.

Database tests cover: employee create/retrieve, duplicate `emp_id` rejection, update,
delete, payroll save and history, history after employee edit, history after employee delete
(FK cleared, snapshot kept), Decimal exactness, persistence after the engine is disposed and
recreated, unreachable-database errors, backend selection, migration import, repeatability,
non-overwrite, invalid-row reporting, dry-run, and a full Flask workflow against the
database store.

### Live checks against PostgreSQL 18.6

| Check | Result |
| --- | --- |
| `python scripts/init_db.py` applying `001_init_schema.sql` | tables, 8/15 columns, 7 indexes created |
| Migration (see section 6) | 7 employees, 6 payroll rows, 6 distinct source_refs, all linked |
| Stored totals | `sum(net_salary) = 425,600.00`, `sum(gross) = 461,500.00`, `sum(deductions) = 35,900.00` - equal to the CSV data and the UI |
| `DELETE FROM employees WHERE emp_id='EMP001'` | payroll row kept, `employee_id` set to `NULL` |
| Flask app on port 5001 with `DATABASE_URL` | `/`, `/employees`, `/employees/EMP001/edit`, `/payroll/new`, `/payroll`, `/payroll/1`, `/analytics` all HTTP 200; dashboard shows 425,600.00 |
| Employee created through the web form | HTTP 302, row inserted in PostgreSQL |
| Application restart (server stopped and started again) | the new employee and all 6 payroll records were still served from PostgreSQL |
| `DATABASE_URL` pointing at a closed port | HTTP **503** with the "Database unavailable" page; error logged, no traceback exposed |
| `python scripts/export_db_to_csv.py` | 8 employees, 6 payroll records exported with the original headers |
| CSV backend unchanged (`PAYROLL_STORAGE=csv`) | all pages and all 53 tests still work |

### Bugs found and fixed during verification

1. `CHECK (length(btrim(...)))` was PostgreSQL-only and broke the SQLite test schema;
   replaced with the standard `trim()` in both the SQL file and the SQLAlchemy metadata.
2. `INSERT ... ON CONFLICT DO NOTHING` reports `rowcount == -1` through psycopg, so
   successful imports were counted as skipped; the insert now uses `RETURNING id` and checks
   for a returned row.
3. Dry-run counted duplicate CSV lines twice; removed rows are now tracked like the real
   insert path does.

---

## 8. Files

**Added**

```
migrations/001_init_schema.sql     schema, constraints, indexes, trigger, RLS
storage/database.py                env loading, URL normalisation, engine factory
storage/database_store.py          PostgreSQL repository (all SQL)
storage/schema.py                  SQLAlchemy table definitions (mirrors the SQL file)
storage/backend.py                 backend selection (get_store / set_store)
storage/migration.py               backup, validation, dedupe, logging
scripts/init_db.py                 apply or check the schema
scripts/migrate_csv_to_supabase.py migration CLI
scripts/export_db_to_csv.py        database -> CSV export
tests/test_database.py             18 database tests
tests/conftest.py                  storage isolation guard
.env.example                       placeholders only
docs/SUPABASE_INTEGRATION.md       this report
```

**Modified (no behaviour or UI change)**

```
services/employee_service.py       delegates to get_store()
services/payroll_service.py        history from get_store()
app.py                             save_payroll via get_store(); init_storage(); 503 handler
main.py                            console uses get_store()/init_storage()
analytics/salary_analysis.py       builds the DataFrame from the store
analytics/charts.py                signature cache; PNG streamed in memory
storage/csv_manager.py             added update/delete/signature/name (unchanged behaviour)
requirements.txt                   sqlalchemy, psycopg[binary], python-dotenv added
.gitignore                         .env, logs/, data/backups/, data/exports/
README.md / docs/FINAL_REPORT.md   database setup section and updated test counts
```

---

## 9. What was NOT verified

Stated plainly, because these claims would otherwise be unsupported:

1. **No live Supabase project connection.** No `DATABASE_URL` or password was provided, so
   the schema and repository were verified against a **local PostgreSQL 18.6 server**
   (temporary cluster, same engine family and SQL dialect), not against
   `*.supabase.co`. Supabase-specific behaviour (pooler routing, connection limits, SSL
   handshake, the dashboard's SQL editor) is untested from here.
2. **No Vercel deployment** was attempted, per instruction. Nothing is proven about
   serverless cold starts or the 6543 pooler in practice.
3. **No load or concurrency test.** `NullPool` plus PostgreSQL handles concurrent writers,
   but no parallel-session test was run.
4. **Chart files - since fixed.** This report's charts were written as PNG files into
   `charts/`, which a read-only serverless filesystem cannot do. Charts are now rendered in
   memory and streamed from `/charts/<filename>`; `docs/DEPLOYMENT_READINESS.md` records the
   change and its tests.
5. **RLS was enabled but only exercised as the table owner**, which bypasses row security.
   Connecting with a restricted Supabase role is untested.

---

## 10. How to run against Supabase

```bash
# 1. Copy the template and fill in your own connection string
cp .env.example .env

# 2. Create the tables (Dashboard -> SQL Editor, or this script)
python scripts/init_db.py

# 3. Import the existing CSV data (backs up first, safe to re-run)
python scripts/migrate_csv_to_supabase.py --dry-run
python scripts/migrate_csv_to_supabase.py

# 4. Start the app - it now reads and writes PostgreSQL
python app.py

# 5. Optional: export the database back to CSV
python scripts/export_db_to_csv.py
```

To keep working offline, set `PAYROLL_STORAGE=csv` (or remove `DATABASE_URL`).
