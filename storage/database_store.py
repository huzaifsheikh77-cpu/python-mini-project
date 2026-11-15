"""PostgreSQL (Supabase) repository for employees and payroll records.

The class exposes the same operations as ``CSVManager`` so the service layer
and the Flask routes stay unchanged. All SQL lives here - no route contains a
query, and no business rule is duplicated.
"""

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models.employee import Employee

from storage import schema
from storage.database import StorageError, create_db_engine


MONEY_PLACES = Decimal("0.01")

PAYROLL_COLUMNS = (
    "emp_id",
    "name",
    "department",
    "basic_salary",
    "hra",
    "other_allowances",
    "pf_deduction",
    "professional_tax",
    "gross_salary",
    "total_deductions",
    "net_salary",
)


def _money(value):
    """Convert a value to a Decimal rounded to two places (exact for money)."""

    return Decimal(str(value)).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _row_to_employee(row):
    return Employee(
        emp_id=row["emp_id"],
        name=row["name"],
        department=row["department"],
        designation=row["designation"],
        basic_salary=row["basic_salary"],
    )


def payroll_values(payroll):
    """Build the column values for one payroll record.

    Amounts are rounded to two places before the totals are derived, so the
    row satisfies the database consistency checks exactly as PostgreSQL will
    store it.
    """

    basic = _money(payroll.employee.basic_salary)
    hra = _money(payroll.hra)
    allowances = _money(payroll.other_allowances)
    pf = _money(payroll.pf_deduction)
    tax = _money(payroll.professional_tax)

    gross = basic + hra + allowances
    deductions = pf + tax

    return {
        "emp_id": payroll.employee.emp_id,
        "name": payroll.employee.name,
        "department": payroll.employee.department,
        "basic_salary": basic,
        "hra": hra,
        "other_allowances": allowances,
        "pf_deduction": pf,
        "professional_tax": tax,
        "gross_salary": gross,
        "total_deductions": deductions,
        "net_salary": gross - deductions,
    }


class DatabaseStore:
    """Supabase PostgreSQL storage backend."""

    name = "database"

    def __init__(self, engine=None):
        # The engine is created lazily so that selecting the backend never
        # opens a connection on import.
        self._engine = engine

    @property
    def engine(self):
        if self._engine is None:
            self._engine = create_db_engine()

        return self._engine

    # --------------------------
    # SCHEMA
    # --------------------------

    def initialize_files(self):
        """Verify the schema exists (SQLite test databases are created here)."""

        try:
            if self.engine.dialect.name == "sqlite":
                schema.metadata.create_all(self.engine)
                return True

            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1 FROM employees LIMIT 1"))

            return True

        except SQLAlchemyError as error:
            raise StorageError(
                "The database schema is missing or unreachable. "
                "Run 'python scripts/init_db.py' to create it. "
                f"({type(error).__name__})"
            ) from error

    # --------------------------
    # EMPLOYEES
    # --------------------------

    def save_employee(self, employee):
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    insert(schema.employees).values(
                        emp_id=employee.emp_id,
                        name=employee.name,
                        department=employee.department,
                        designation=employee.designation,
                        basic_salary=_money(employee.basic_salary),
                    )
                )

        except IntegrityError as error:
            raise ValueError("Employee ID already exists.") from error

        except SQLAlchemyError as error:
            raise StorageError(f"Could not save the employee. ({type(error).__name__})") from error

    def import_employee_row(self, employee):
        """Insert an employee unless the emp_id already exists.

        Returns True when a row was inserted, False when it was skipped.
        Existing rows are never overwritten.
        """

        values = {
            "emp_id": employee.emp_id,
            "name": employee.name,
            "department": employee.department,
            "designation": employee.designation,
            "basic_salary": _money(employee.basic_salary),
        }

        try:
            with self.engine.begin() as connection:
                return self._insert_ignoring_conflicts(
                    connection, schema.employees, values, ["emp_id"]
                )

        except SQLAlchemyError as error:
            raise StorageError(f"Could not import the employee. ({type(error).__name__})") from error

    def load_employees(self):
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    select(schema.employees).order_by(schema.employees.c.id)
                ).mappings().all()

        except SQLAlchemyError as error:
            raise StorageError(f"Could not read employees. ({type(error).__name__})") from error

        return [_row_to_employee(row) for row in rows]

    def update_employee(self, emp_id, name=None, department=None,
                        designation=None, basic_salary=None):
        try:
            with self.engine.begin() as connection:
                existing = connection.execute(
                    select(schema.employees).where(schema.employees.c.emp_id == emp_id)
                ).mappings().first()

                if existing is None:
                    return None

                values = {
                    "name": name if name is not None else existing["name"],
                    "department": department if department is not None else existing["department"],
                    "designation": designation if designation is not None else existing["designation"],
                    "basic_salary": _money(
                        basic_salary if basic_salary is not None else existing["basic_salary"]
                    ),
                    "updated_at": func.now(),
                }

                connection.execute(
                    update(schema.employees)
                    .where(schema.employees.c.emp_id == emp_id)
                    .values(**values)
                )

                updated = connection.execute(
                    select(schema.employees).where(schema.employees.c.emp_id == emp_id)
                ).mappings().one()

        except IntegrityError as error:
            raise ValueError("Employee could not be updated with those values.") from error

        except SQLAlchemyError as error:
            raise StorageError(f"Could not update the employee. ({type(error).__name__})") from error

        return _row_to_employee(updated)

    def delete_employee(self, emp_id):
        """Delete an employee. Payroll history is kept (FK set to NULL)."""

        try:
            with self.engine.begin() as connection:
                result = connection.execute(
                    delete(schema.employees).where(schema.employees.c.emp_id == emp_id)
                )

        except SQLAlchemyError as error:
            raise StorageError(f"Could not delete the employee. ({type(error).__name__})") from error

        return result.rowcount > 0

    def replace_employees(self, employees):
        """Rewrite the employee table from a list (interface parity with CSV)."""

        keep = [employee.emp_id for employee in employees]

        try:
            with self.engine.begin() as connection:
                if keep:
                    connection.execute(
                        delete(schema.employees).where(
                            schema.employees.c.emp_id.not_in(keep)
                        )
                    )
                else:
                    connection.execute(delete(schema.employees))

                for employee in employees:
                    values = {
                        "emp_id": employee.emp_id,
                        "name": employee.name,
                        "department": employee.department,
                        "designation": employee.designation,
                        "basic_salary": _money(employee.basic_salary),
                    }

                    result = connection.execute(
                        update(schema.employees)
                        .where(schema.employees.c.emp_id == employee.emp_id)
                        .values(
                            name=values["name"],
                            department=values["department"],
                            designation=values["designation"],
                            basic_salary=values["basic_salary"],
                            updated_at=func.now(),
                        )
                    )

                    if result.rowcount == 0:
                        connection.execute(insert(schema.employees).values(**values))

        except SQLAlchemyError as error:
            raise StorageError(f"Could not replace employees. ({type(error).__name__})") from error

    # --------------------------
    # PAYROLL
    # --------------------------

    def _linked_employee_id(self, connection, emp_id):
        row = connection.execute(
            select(schema.employees.c.id).where(schema.employees.c.emp_id == emp_id)
        ).first()

        return row[0] if row else None

    def save_payroll(self, payroll, source_ref=None):
        values = payroll_values(payroll)

        try:
            with self.engine.begin() as connection:
                values["employee_id"] = self._linked_employee_id(
                    connection, payroll.employee.emp_id
                )
                values["source_ref"] = source_ref

                connection.execute(insert(schema.payroll_records).values(**values))

        except IntegrityError as error:
            raise ValueError(
                "The payroll record violates a database constraint."
            ) from error

        except SQLAlchemyError as error:
            raise StorageError(f"Could not save the payroll record. ({type(error).__name__})") from error

    def import_payroll_row(self, payroll, source_ref):
        """Insert a payroll row unless its source_ref was already imported."""

        values = payroll_values(payroll)
        values["source_ref"] = source_ref

        try:
            with self.engine.begin() as connection:
                values["employee_id"] = self._linked_employee_id(
                    connection, payroll.employee.emp_id
                )

                return self._insert_ignoring_conflicts(
                    connection, schema.payroll_records, values, ["source_ref"]
                )

        except SQLAlchemyError as error:
            raise StorageError(f"Could not import the payroll record. ({type(error).__name__})") from error

    def load_payroll_records(self):
        """Return payroll rows in insertion order as dictionaries.

        Keys and value types match the CSV backend so ``PayrollService``,
        the templates and the analytics layer work unchanged.
        """

        columns = [
            schema.payroll_records.c[column] for column in PAYROLL_COLUMNS
        ]

        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    select(*columns).order_by(schema.payroll_records.c.id)
                ).mappings().all()

        except SQLAlchemyError as error:
            raise StorageError(f"Could not read payroll records. ({type(error).__name__})") from error

        records = []

        for index, row in enumerate(rows, start=1):
            record = {"record_number": index}

            for column in PAYROLL_COLUMNS:
                value = row[column]
                record[column] = _money(value) if column not in ("emp_id", "name", "department") else value

            records.append(record)

        return records

    def existing_source_refs(self):
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    select(schema.payroll_records.c.source_ref).where(
                        schema.payroll_records.c.source_ref.is_not(None)
                    )
                ).all()

        except SQLAlchemyError as error:
            raise StorageError(f"Could not read payroll source refs. ({type(error).__name__})") from error

        return {row[0] for row in rows}

    # --------------------------
    # HELPERS
    # --------------------------

    def data_signature(self):
        """Cheap fingerprint of the payroll table, used to refresh charts."""

        try:
            with self.engine.connect() as connection:
                row = connection.execute(
                    select(
                        func.count(schema.payroll_records.c.id),
                        func.max(schema.payroll_records.c.id),
                        func.max(schema.payroll_records.c.processed_at),
                    )
                ).one()

        except SQLAlchemyError as error:
            raise StorageError(f"Could not read the data signature. ({type(error).__name__})") from error

        return f"db:{row[0]}:{row[1]}:{row[2]}"

    def counts(self):
        with self.engine.connect() as connection:
            employees = connection.execute(
                select(func.count(schema.employees.c.id))
            ).scalar_one()
            payroll = connection.execute(
                select(func.count(schema.payroll_records.c.id))
            ).scalar_one()

        return {"employees": int(employees), "payroll_records": int(payroll)}

    def _insert_ignoring_conflicts(self, connection, table, values, conflict_columns):
        """INSERT ... ON CONFLICT DO NOTHING for PostgreSQL and SQLite.

        Uses RETURNING because psycopg reports ``rowcount == -1`` for
        INSERT ... ON CONFLICT, which would make successful inserts look like
        conflicts.
        """

        dialect = connection.dialect.name

        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as dialect_insert

            statement = (
                dialect_insert(table)
                .values(**values)
                .on_conflict_do_nothing(index_elements=conflict_columns)
                .returning(table.c.id)
            )

        elif dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as dialect_insert

            statement = (
                dialect_insert(table)
                .values(**values)
                .on_conflict_do_nothing(index_elements=conflict_columns)
                .returning(table.c.id)
            )

        else:
            statement = insert(table).values(**values).returning(table.c.id)

        return connection.execute(statement).first() is not None
