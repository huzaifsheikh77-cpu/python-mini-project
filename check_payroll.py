
from storage.csv_manager import CSVManager

records = CSVManager.load_payroll_records()

print("Number of records:", len(records))

for record in records:
    print(
        record["emp_id"],
        record["name"],
        record["net_salary"]
    )
