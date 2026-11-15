"""SQLAlchemy Core table definitions.

``migrations/001_init_schema.sql`` is the authoritative schema for Supabase
PostgreSQL. These table objects mirror it exactly and are used by the
repository, by ``scripts/init_db.py`` for local SQLite databases and by the
database tests.
"""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    func,
    text,
)


MONEY = Numeric(14, 2)

# BIGSERIAL on PostgreSQL, INTEGER on SQLite so the column stays a rowid alias.
PkType = BigInteger().with_variant(Integer, "sqlite")
FkType = BigInteger().with_variant(Integer, "sqlite")

metadata = MetaData()


employees = Table(
    "employees",
    metadata,
    Column("id", PkType, primary_key=True, autoincrement=True),
    Column("emp_id", String(40), nullable=False, unique=True),
    Column("name", String(120), nullable=False),
    Column("department", String(80), nullable=False),
    Column("designation", String(80), nullable=False),
    Column("basic_salary", MONEY, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("length(trim(name)) > 0", name="employees_name_not_blank"),
    CheckConstraint("length(trim(department)) > 0", name="employees_department_not_blank"),
    CheckConstraint("length(trim(designation)) > 0", name="employees_designation_not_blank"),
    CheckConstraint("basic_salary > 0", name="employees_basic_salary_positive"),
)


payroll_records = Table(
    "payroll_records",
    metadata,
    Column("id", PkType, primary_key=True, autoincrement=True),
    Column(
        "employee_id",
        FkType,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    ),
    # Snapshot columns: payroll history must survive edits and deletions.
    Column("emp_id", String(40), nullable=False),
    Column("name", String(120), nullable=False),
    Column("department", String(80), nullable=False),
    Column("basic_salary", MONEY, nullable=False),
    Column("hra", MONEY, nullable=False, server_default=text("0")),
    Column("other_allowances", MONEY, nullable=False, server_default=text("0")),
    Column("pf_deduction", MONEY, nullable=False, server_default=text("0")),
    Column("professional_tax", MONEY, nullable=False, server_default=text("0")),
    Column("gross_salary", MONEY, nullable=False),
    Column("total_deductions", MONEY, nullable=False),
    Column("net_salary", MONEY, nullable=False),
    # Stable identifier of the originating row, used to make CSV import repeatable.
    Column("source_ref", String(120), nullable=True),
    Column("processed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("basic_salary > 0", name="payroll_basic_salary_positive"),
    CheckConstraint("hra >= 0", name="payroll_hra_non_negative"),
    CheckConstraint("other_allowances >= 0", name="payroll_allowances_non_negative"),
    CheckConstraint("pf_deduction >= 0", name="payroll_pf_non_negative"),
    CheckConstraint("professional_tax >= 0", name="payroll_tax_non_negative"),
    CheckConstraint("gross_salary >= 0", name="payroll_gross_non_negative"),
    CheckConstraint("total_deductions >= 0", name="payroll_deductions_non_negative"),
    CheckConstraint("net_salary >= 0", name="payroll_net_non_negative"),
)


Index("employees_department_idx", employees.c.department)
Index("employees_name_idx", func.lower(employees.c.name))

# A plain unique index allows many NULLs (application-created rows) while
# preventing two imports of the same CSV row.
Index("payroll_source_ref_uidx", payroll_records.c.source_ref, unique=True)

Index("payroll_employee_idx", payroll_records.c.employee_id)
Index("payroll_emp_id_idx", payroll_records.c.emp_id)
Index("payroll_processed_at_idx", payroll_records.c.processed_at.desc())
