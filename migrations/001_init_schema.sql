-- ============================================================================
-- Employee Payroll Management System - Supabase / PostgreSQL schema
-- Run once in the Supabase SQL editor (or: python scripts/init_db.py).
-- The script is idempotent: running it again changes nothing.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- employees: current master data
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    id           BIGSERIAL     PRIMARY KEY,
    emp_id       VARCHAR(40)   NOT NULL UNIQUE,
    name         VARCHAR(120)  NOT NULL,
    department   VARCHAR(80)   NOT NULL,
    designation  VARCHAR(80)   NOT NULL,
    basic_salary NUMERIC(14,2) NOT NULL,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),

    CONSTRAINT employees_emp_id_not_blank
        CHECK (length(trim(emp_id)) > 0),
    CONSTRAINT employees_name_not_blank
        CHECK (length(trim(name)) > 0),
    CONSTRAINT employees_department_not_blank
        CHECK (length(trim(department)) > 0),
    CONSTRAINT employees_designation_not_blank
        CHECK (length(trim(designation)) > 0),
    CONSTRAINT employees_basic_salary_positive
        CHECK (basic_salary > 0)
);

CREATE INDEX IF NOT EXISTS employees_department_idx
    ON employees (department);

CREATE INDEX IF NOT EXISTS employees_name_idx
    ON employees (lower(name));

-- ---------------------------------------------------------------------------
-- payroll_records: one row per processed payroll transaction.
-- Employee details are stored as a snapshot (emp_id, name, department,
-- basic_salary) so history stays correct after the employee is edited or
-- deleted. employee_id is a nullable link that is set to NULL on delete.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payroll_records (
    id                 BIGSERIAL     PRIMARY KEY,
    employee_id        BIGINT        NULL,
    emp_id             VARCHAR(40)   NOT NULL,
    name               VARCHAR(120)  NOT NULL,
    department         VARCHAR(80)   NOT NULL,
    basic_salary       NUMERIC(14,2) NOT NULL,
    hra                NUMERIC(14,2) NOT NULL DEFAULT 0,
    other_allowances   NUMERIC(14,2) NOT NULL DEFAULT 0,
    pf_deduction       NUMERIC(14,2) NOT NULL DEFAULT 0,
    professional_tax   NUMERIC(14,2) NOT NULL DEFAULT 0,
    gross_salary       NUMERIC(14,2) NOT NULL,
    total_deductions   NUMERIC(14,2) NOT NULL,
    net_salary         NUMERIC(14,2) NOT NULL,
    source_ref         VARCHAR(120)  NULL,
    processed_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),

    CONSTRAINT payroll_employee_fk
        FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE SET NULL,

    CONSTRAINT payroll_basic_salary_positive   CHECK (basic_salary > 0),
    CONSTRAINT payroll_hra_non_negative         CHECK (hra >= 0),
    CONSTRAINT payroll_allowances_non_negative  CHECK (other_allowances >= 0),
    CONSTRAINT payroll_pf_non_negative          CHECK (pf_deduction >= 0),
    CONSTRAINT payroll_tax_non_negative         CHECK (professional_tax >= 0),
    CONSTRAINT payroll_gross_non_negative       CHECK (gross_salary >= 0),
    CONSTRAINT payroll_deductions_non_negative  CHECK (total_deductions >= 0),
    CONSTRAINT payroll_net_non_negative         CHECK (net_salary >= 0),
    CONSTRAINT payroll_net_consistent
        CHECK (net_salary = gross_salary - total_deductions),
    CONSTRAINT payroll_gross_consistent
        CHECK (gross_salary = basic_salary + hra + other_allowances)
);

-- Repeatable CSV imports: one row per originating CSV line, many NULLs
-- allowed for records created through the web application.
CREATE UNIQUE INDEX IF NOT EXISTS payroll_source_ref_uidx
    ON payroll_records (source_ref);

CREATE INDEX IF NOT EXISTS payroll_employee_idx
    ON payroll_records (employee_id);

CREATE INDEX IF NOT EXISTS payroll_emp_id_idx
    ON payroll_records (emp_id);

CREATE INDEX IF NOT EXISTS payroll_processed_at_idx
    ON payroll_records (processed_at DESC);

-- ---------------------------------------------------------------------------
-- Keep employees.updated_at accurate without any application code.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS employees_set_updated_at ON employees;

CREATE TRIGGER employees_set_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Row level security: the application connects as the database owner, so RLS
-- is enabled with no public policies (safe default if the anon key is ever
-- used from a browser).
-- ---------------------------------------------------------------------------
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_records ENABLE ROW LEVEL SECURITY;
