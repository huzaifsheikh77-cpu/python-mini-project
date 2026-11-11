
import pandas as pd

from storage.csv_manager import PAYROLL_FILE


class SalaryAnalysis:

    @staticmethod
    def load_data():
        try:
            df = pd.read_csv(PAYROLL_FILE)

            if df.empty:
                print("No payroll records available.")
                return None

            return df

        except FileNotFoundError:
            print("Payroll database not found.")
            return None

    @staticmethod
    def display_summary():

        df = SalaryAnalysis.load_data()

        if df is None:
            return

        print("\n===== PAYROLL SUMMARY =====")

        print("Total payroll records:", len(df))

        print(
            "Total salary expenditure:",
            df["net_salary"].sum()
        )

        print(
            "Average net salary:",
            df["net_salary"].mean()
        )

        print(
            "Highest net salary:",
            df["net_salary"].max()
        )

        print(
            "Lowest net salary:",
            df["net_salary"].min()
        )

    @staticmethod
    def department_analysis():

        df = SalaryAnalysis.load_data()

        if df is None:
            return

        result = (
            df.groupby("department")["net_salary"]
            .sum()
            .sort_values(ascending=False)
        )

        print("\n===== DEPARTMENT PAYROLL =====")
        print(result)
