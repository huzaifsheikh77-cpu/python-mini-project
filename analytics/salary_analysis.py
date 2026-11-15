import pandas as pd

from storage.backend import get_store
from storage.database import StorageError


# ==============================
# SALARY ANALYSIS
# ==============================

class SalaryAnalysis:
    """Pandas based analysis of the stored payroll records."""

    # Monetary columns are converted to float for analysis only; the stored
    # values keep their exact Decimal representation.
    NUMERIC_COLUMNS = (
        "basic_salary",
        "hra",
        "other_allowances",
        "pf_deduction",
        "professional_tax",
        "gross_salary",
        "total_deductions",
        "net_salary",
    )

    @staticmethod
    def load_data(quiet=True):
        """Load payroll records from the active store into a DataFrame."""

        try:
            records = get_store().load_payroll_records()

        except StorageError as error:
            if not quiet:
                print("Payroll data could not be loaded:", error)
            return None

        if not records:
            if not quiet:
                print("No payroll records available.")
            return None

        df = pd.DataFrame(records)

        if "record_number" in df.columns:
            df = df.drop(columns=["record_number"])

        for column in SalaryAnalysis.NUMERIC_COLUMNS:
            df[column] = [float(value) for value in df[column]]

        if df.empty:
            if not quiet:
                print("No payroll records available.")
            return None

        return df

    @staticmethod
    def summary(df=None):
        """Overall payroll statistics as a dictionary."""

        df = SalaryAnalysis.load_data() if df is None else df

        if df is None:
            return None

        return {
            "total_records": int(len(df)),
            "total_expenditure": float(df["net_salary"].sum()),
            "average_salary": float(df["net_salary"].mean()),
            "highest_salary": float(df["net_salary"].max()),
            "lowest_salary": float(df["net_salary"].min()),
        }

    @staticmethod
    def department_summary(df=None):
        """Department-wise payroll totals as a list of dictionaries."""

        df = SalaryAnalysis.load_data() if df is None else df

        if df is None:
            return []

        grouped = (
            df.groupby("department")
            .agg(
                employees=("net_salary", "size"),
                total=("net_salary", "sum"),
                average=("net_salary", "mean"),
            )
            .sort_values("total", ascending=False)
        )

        return [
            {
                "department": department,
                "employees": int(row.employees),
                "total": float(row.total),
                "average": float(row.average),
            }
            for department, row in grouped.iterrows()
        ]

    # --------------------------
    # CONSOLE (CLI) OUTPUT
    # --------------------------

    @staticmethod
    def display_summary():
        summary = SalaryAnalysis.summary()

        if summary is None:
            return

        print("\n===== PAYROLL SUMMARY =====")
        print("Total payroll records:", summary["total_records"])
        print("Total salary expenditure:", summary["total_expenditure"])
        print("Average net salary:", summary["average_salary"])
        print("Highest net salary:", summary["highest_salary"])
        print("Lowest net salary:", summary["lowest_salary"])

    @staticmethod
    def department_analysis():
        rows = SalaryAnalysis.department_summary()

        if not rows:
            return

        print("\n===== DEPARTMENT PAYROLL =====")

        for row in rows:
            print(f"{row['department']}: {row['total']}")
