# Deployment Readiness Report - Employee Payroll Management System

**Date:** 15 November 2026
**Scope:** Supabase verification, in-memory charts, Vercel serverless compatibility, security review
**Status:** Chart and serverless work complete and tested; **live Supabase verification not run** (no credentials were present in `.env`), so nothing was deployed.

---

## 1. Summary

| Area | Result |
| --- | --- |
| Charts on serverless | **Fixed** - rendered in memory, streamed as PNG, no filesystem writes |
| Vercel entry point and config | **Added** - `api/index.py`, `vercel.json` |
| Production debug mode | **Off** on Vercel (WSGI import never calls `app.run()`); local debug behind `PAYROLL_DEBUG` |
| Database lifecycle | Serverless-safe - `NullPool`, `pool_pre_ping`, pooler URL documented |
| Routes | **Unchanged** - same 13 rules, same endpoints, same URLs |
| Test suite | **53 passed** (was 49; 4 chart-response tests added, 1 rewritten) |
| Live Supabase connection | **Not verified** - `DATABASE_URL` was not set in `.env` |
| Vercel deployment | **Not performed** (explicitly out of scope) |

---

## 2. Charts: from files to memory

### What was wrong

`/analytics` called `PayrollCharts.ensure_charts()`, which drew three Matplotlib figures and
wrote `charts/*.png` with `plt.savefig()`. `/charts/<filename>` then served that file with
`send_from_directory()`. Vercel's function filesystem is read-only apart from `/tmp`, so the
analytics page would fail (or, worse, succeed per-container and disappear on the next cold
start).

### What it does now

| Step | Implementation |
| --- | --- |
| Draw | One `matplotlib.figure.Figure` on a `FigureCanvasAgg` per request - no `pyplot` global state, safe for concurrent requests |
| Output | `figure.savefig(BytesIO(), format="png", dpi=130)` |
| Serve | `/charts/<filename>` returns `send_file(BytesIO(...), mimetype="image/png")` |
| Cache | PNG bytes are cached in memory per chart and per `data_signature()`, so repeat views reuse the image until payroll data changes |
| Errors | Missing data → placeholder PNG ("No payroll records to chart yet"). Rendering exception → logged (`app.logger.exception`) and a placeholder PNG ("This chart could not be generated"). Unknown filename → 404 as before |
| Disk | **No write happens during a web request.** `generate_charts()` remains for the console version and offline PNGs |

**Appearance preserved:** the drawing code (colours, figure sizes, DPI, labels, grid, bar
annotations, pie percentages) is unchanged, only the output target. For the current data,
the streamed images are byte-for-byte the same size as the previously generated files
(43,185 / 68,415 / 30,555 bytes).

**UI preserved:** `templates/analytics.html` was not edited. It still receives
`chart_urls.department`, `chart_urls.comparison`, `chart_urls.distribution` and a
`cache_token`, so the markup, the "Regenerate charts" link and the empty state are identical.

**Local development preserved:** CSV mode, `python app.py`, the console version
(`main.py` → `generate_charts()`) and `charts/*.png` all behave as before.

---

## 3. Vercel serverless compatibility

| Check | Status | Evidence |
| --- | --- | --- |
| Flask entry point | OK | `api/index.py` adds the project root to `sys.path` and exports `app` (WSGI callable). Importing it as Vercel does produced a callable app with 13 routes |
| Vercel configuration | OK | `vercel.json` builds `api/index.py` with `@vercel/python`, bundles `app.py`, `models/`, `services/`, `storage/`, `analytics/`, `templates/`, `static/`, `migrations/`, and routes `/(.*)` to the function. Validated as JSON |
| Static assets | OK | `static/` is bundled with the function and served by Flask; requests never depend on the project filesystem being writable |
| Templates | OK | `templates/` is bundled and resolved from the project root, the same path used locally |
| Database lifecycle | OK | `NullPool` + `pool_pre_ping`; each request opens and closes its own connection through the Supabase transaction pooler (port 6543, `sslmode=require`) |
| Chart endpoints | OK | Render in memory; no writes; graceful placeholder on failure |
| Environment variables | OK | `DATABASE_URL`, `PAYROLL_STORAGE`, `PAYROLL_SECRET_KEY`, `PAYROLL_DEBUG` read via `os.environ` / `python-dotenv`; `.env` is local-only and git-ignored |
| Debug mode in production | OK | Vercel imports the WSGI app; `app.run(debug=...)` runs only under `__main__`. Local default remains debug on, `PAYROLL_DEBUG=0` turns it off |
| Permanent data on the Vercel filesystem | None | All application data is in Supabase; charts are in memory. Only `charts/` (CLI) and `logs/`, `data/backups/` (scripts) write locally, and none of those run during a request |
| Existing routes unchanged | OK | Route table before/after is identical (dashboard, employees CRUD, payroll new/save/history/record, analytics, chart_image, api_calculate) |

### Verified locally

- **CSV backend** (port 5000): `/`, `/analytics` 200; all three chart URLs return
  `200 image/png`; unknown chart returns 404; `charts/` mtimes unchanged → no writes.
- **Database backend** (SQLite stand-in, port 5051): schema created, CSVs migrated
  (7 employees / 6 payroll rows), pages 200, charts `200 image/png`, analytics total
  Rs. 425,600.00 (matches the CSV data), application still healthy after chart requests.

Not verified: an actual Vercel build/deploy, cold starts, and the function bundle size with
matplotlib + pandas + numpy (see blockers).

---

## 4. Supabase verification: not run

**`DATABASE_URL` is not set in this workspace's `.env`** (no `.env` file exists yet), so no
Supabase connection, migration or CRUD check against the live project was possible. Nothing
in this report should be read as a successful Supabase test.

To run the full verification yourself, create `.env` from `.env.example`, put the pooler URI
in `DATABASE_URL` (port 6543, `sslmode=require`), then:

```bash
python scripts/init_db.py                     # create and verify the schema
python scripts/verify_supabase.py             # full verification, one command
```

`scripts/verify_supabase.py` performs, with `[OK]`/`[FAIL]` lines and a non-zero exit code on
failure:

1. Connect through the pooler; print host/port/database/sslmode (never the password or user).
2. Confirm the connection actually uses SSL (`pg_stat_ssl`).
3. Confirm the schema exists, and show current row counts.
4. Compare the database against the CSV baseline (employee count, payroll count, net total).
5. Run the migration **dry run** and confirm it changes nothing.
6. Run the real migration; check no rejected rows, counts and totals matching the CSVs, and
   that existing rows were not overwritten (counts never decrease).
7. Re-run the migration to prove idempotency (0 imported) and unchanged counts.
8. CRUD with a temporary id (`VERIFY-<time>`): insert, read, update, save a payroll record,
   check the history snapshot keeps the original salary, delete the employee and confirm the
   payroll row survives with its foreign key cleared, then remove the temporary rows.
9. Reconnect with a fresh engine to prove the records persist.

Run `python scripts/verify_supabase.py --read-only` for connection and schema only.

The script prints a redacted target line and never echoes credentials.

---

## 5. Security review

| Item | Status |
| --- | --- |
| `.env` excluded from Git | Yes - `.gitignore` lines 11-12 (`.env`, `.env.local`); `git ls-files` shows no `.env*` |
| `.env.example` placeholders only | Yes - `<project-ref>`, `<region>`, `<password>`; no real values |
| Service-role / anon key exposure | None. The app connects server-side with the database URL only; no Supabase key exists in code, templates or JS. A repository-wide search for `service_role`, `SUPABASE_KEY`, `SUPABASE_ANON` and JWT prefixes found nothing |
| Secrets in responses | The 503 "Database unavailable" page and the 500 handler show a friendly message; the connection string is never rendered, only logged server-side |
| Authentication | **Absent, by design.** Anyone with the URL can read, edit and delete records. The application must **not** be presented as suitable for real employee payroll data |
| Demo data | Fictional - `data/DEMO_DATA.txt` states the names, salaries and amounts are made up for demonstration |
| Debug mode | Off in production; local debug is now controllable with `PAYROLL_DEBUG` |
| CSRF | **Not implemented.** Acceptable only while there is no login; needed before any real deployment |
| Rate limiting | None |

Documented in `README.md` (limitations and the Vercel subsection) so the public deployment is
never described as secure for real payroll data.

Authentication was **not** added, per instruction.

---

## 6. Tests

```
53 passed in 6.17s
```

| File | Tests | Change |
| --- | --- | --- |
| `test_employee.py` | 3 | unchanged |
| `test_payroll.py` | 5 | unchanged |
| `test_csv.py` | 5 | unchanged |
| `test_web.py` | 22 | 1 test rewritten, 4 added |
| `test_database.py` | 18 | unchanged |

New expectations in `test_web.py`:

- the analytics page links `/charts/...` and leaves `charts/` empty (no files written);
- `/charts/salary_comparison.png` returns `200 image/png` with PNG bytes;
- an unknown chart name returns 404;
- with no payroll data the endpoint returns a placeholder PNG;
- when the renderer raises, the endpoint still returns `200 image/png` (placeholder) and logs.

The suite still passes on the CSV backend and on the database backend (SQLite per test);
`test_database.py` can also run against PostgreSQL via `PAYROLL_TEST_DATABASE_URL`.

---

## 7. Files changed in this mission

| File | Change |
| --- | --- |
| `analytics/charts.py` | Rewritten: figure-based rendering, `render_png()`, in-memory cache, `placeholder_png()`, `ChartUnavailable`, `key_for_filename()`; file output kept for the CLI |
| `app.py` | `/analytics` no longer generates files (signature-based cache token); `/charts/<filename>` streams PNG from memory with graceful fallbacks; `PAYROLL_DEBUG` flag; `send_file`/`BytesIO` imports |
| `api/index.py` | **New** - Vercel WSGI entry point |
| `vercel.json` | **New** - build and routing for the serverless function |
| `scripts/verify_supabase.py` | **New** - one-command Supabase + migration verification |
| `tests/test_web.py` | Analytics test rewritten for in-memory charts; 4 chart-endpoint tests added |
| `.env.example` | Added `PAYROLL_DEBUG` with explanation |
| `README.md` | Vercel subsection, security warning, folder tree, limitations, test counts |
| `docs/PROJECT_EXPLANATION.md`, `docs/VIVA.md`, `docs/FINAL_REPORT.md`, `docs/DEMONSTRATION.md`, `docs/SUPABASE_INTEGRATION.md` | Chart architecture, test counts, chart-file caveat |
| `docs/DEPLOYMENT_READINESS.md` | **New** - this report |

Not changed: templates, CSS, payroll formulas, employee/payroll fields, existing routes,
storage schema, migration scripts.

---

## 8. Remaining blockers before a public deployment

1. **Live Supabase verification** - needs `DATABASE_URL` in `.env` (run section 4).
2. **No authentication** - the single largest blocker for real payroll data. Every visitor has
   full read/write access. Needs an approved auth design.
3. **No CSRF protection** - must be added together with authentication.
4. **Function bundle size** - matplotlib + pandas + numpy is large; the first Vercel build must
   confirm it fits the plan's limit. If not, options are a lighter chart implementation or
   client-side charting, both of which change the analytics layer only.
5. **Cold-start latency** - the first request in a new function instance imports pandas and
   matplotlib (typically a second or two).
6. **No concurrency/load test** - `NullPool` with the pooler is the recommended setup, but
   parallel traffic through Supabase's pooler limits has not been measured.
7. **RLS only tested as table owner** - connecting with a restricted role is unverified.
8. **No deployment performed** - nothing was pushed, deployed or published, per instruction.
