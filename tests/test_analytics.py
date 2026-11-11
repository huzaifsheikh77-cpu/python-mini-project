
from analytics.salary_analysis import SalaryAnalysis
from analytics.charts import PayrollCharts


print("\nSTARTING PAYROLL ANALYSIS")

SalaryAnalysis.display_summary()

SalaryAnalysis.department_analysis()

PayrollCharts.generate_charts()
