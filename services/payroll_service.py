from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from models.payroll import Payroll

from storage.backend import get_store


# ==============================
# PAYROLL SERVICE
# ==============================

class PayrollService:
    """Business logic used by the Flask front-end.

    The class keeps validation and summary calculations in one place so the
    web routes stay thin and the CLI can reuse the same rules.
    """

    # --------------------------
    # INPUT PARSING
    # --------------------------

    @staticmethod
    def parse_amount(raw, label, allow_zero=True):
        """Convert form input into a safe non-negative Decimal."""

        if raw is None or str(raw).strip() == "":
            raise ValueError(f"{label} is required.")

        try:
            value = Decimal(str(raw).strip())
        except InvalidOperation:
            raise ValueError(f"{label} must be a number.")

        if not value.is_finite():
            raise ValueError(f"{label} must be a finite number.")

        if value < 0:
            raise ValueError(f"{label} cannot be negative.")

        if not allow_zero and value == 0:
            raise ValueError(f"{label} must be greater than zero.")

        return value

    @staticmethod
    def build(employee, data):
        """Create a Payroll object from a form-like mapping."""

        return Payroll(
            employee=employee,
            hra=PayrollService.parse_amount(data.get("hra"), "HRA"),
            other_allowances=PayrollService.parse_amount(
                data.get("other_allowances"), "Other allowances"
            ),
            pf_deduction=PayrollService.parse_amount(
                data.get("pf_deduction"), "PF deduction"
            ),
            professional_tax=PayrollService.parse_amount(
                data.get("professional_tax"), "Professional tax"
            ),
        )

    # --------------------------
    # STORAGE ACCESS
    # --------------------------

    @staticmethod
    def history():
        """Return saved payroll records, newest first."""

        return list(reversed(get_store().load_payroll_records()))

    @staticmethod
    def find_record(index):
        """Return the saved record at a 1-based position in history."""

        records = PayrollService.history()

        if index < 1 or index > len(records):
            return None

        return records[index - 1]

    # --------------------------
    # SUMMARY CALCULATIONS
    # --------------------------

    @staticmethod
    def summary(records=None):
        """Totals calculated directly from the payroll records."""

        records = PayrollService.history() if records is None else records

        if not records:
            zero = Decimal("0.00")
            return {
                "count": 0,
                "total": zero,
                "average": zero,
                "highest": zero,
                "lowest": zero,
            }

        salaries = [Decimal(str(record["net_salary"])) for record in records]
        total = sum(salaries, Decimal("0"))

        return {
            "count": len(salaries),
            "total": total,
            "average": (total / len(salaries)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "highest": max(salaries),
            "lowest": min(salaries),
        }

    @staticmethod
    def department_totals(records=None):
        """Department-wise payroll totals sorted by highest payout."""

        records = PayrollService.history() if records is None else records

        totals = {}

        for record in records:
            department = record.get("department", "") or "Unassigned"
            net = Decimal(str(record["net_salary"]))

            if department not in totals:
                totals[department] = {"total": Decimal("0"), "count": 0}

            totals[department]["total"] += net
            totals[department]["count"] += 1

        return [
            {
                "department": department,
                "total": values["total"],
                "count": values["count"],
            }
            for department, values in sorted(
                totals.items(),
                key=lambda item: item[1]["total"],
                reverse=True,
            )
        ]
