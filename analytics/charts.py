
import matplotlib.pyplot as plt

from analytics.salary_analysis import SalaryAnalysis

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CHART_DIR = BASE_DIR / "charts"


class PayrollCharts:

    @staticmethod
    def generate_charts():

        df = SalaryAnalysis.load_data()

        if df is None:
            return

        CHART_DIR.mkdir(exist_ok=True)

        # Chart 1: Employee salary comparison
        plt.figure(figsize=(10, 6))

        plt.bar(df["name"], df["net_salary"])

        plt.title("Employee Net Salary Comparison")
        plt.xlabel("Employee")
        plt.ylabel("Net Salary (Rs.)")
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.savefig(CHART_DIR / "salary_comparison.png")
        plt.close()

        # Chart 2: Department-wise payroll
        department_data = (
            df.groupby("department")["net_salary"].sum()
        )

        plt.figure(figsize=(8, 8))

        plt.pie(
            department_data,
            labels=department_data.index,
            autopct="%1.1f%%"
        )

        plt.title("Department-wise Payroll Distribution")

        plt.savefig(CHART_DIR / "department_payroll.png")
        plt.close()

        # Chart 3: Salary distribution
        plt.figure(figsize=(10, 6))

        plt.hist(df["net_salary"], bins=5)

        plt.title("Employee Salary Distribution")
        plt.xlabel("Net Salary (Rs.)")
        plt.ylabel("Number of Records")

        plt.tight_layout()
        plt.savefig(CHART_DIR / "salary_distribution.png")
        plt.close()

        print("\nThree payroll charts generated successfully!")
