import pprint
import urllib.parse
from typing import Dict, List
from mongoengine import connect
import models
import datetime


db_user = "hummingbird_user"
db_password = "Tm5Zt2EzWrX86sSjDq3Bc7"
db_host = "localhost"
db_port = 9010
db_name = "hummingbird_payroll"
DB_URL = f"mongodb://{urllib.parse.quote_plus(db_user)}:{urllib.parse.quote_plus(db_password)}@{db_host}:{db_port}/{db_name}?authSource=admin"
connect(host=DB_URL, uuidRepresentation="standard")

# company = models.Company(name="ACME Ltd", legal_name="ACME Ltd", description="ACME Ltd", pin_number="P051234567A", nssf_number="12345678", shif_number="12345678", nita_number="12345678", contact_email="hr@acme.com", contact_phone="0712345678", address="1234 Acme Street, Acme City")
# company.save()

company = models.Company.objects.first()

# john: models.Staff = models.Staff(first_name="John", last_name="Doe", job_title="Software Engineer", department="Engineering", contact_email="john.doe@acme.com", contact_phone="0712345678", pin_number="12345678", staff_number="12345678", shif_number="12345678", nssf_number="12345678", nita_number="12345678", national_id_number="22113344", date_of_birth=datetime.datetime(1990, 1, 1), is_active=True, joined_on=datetime.datetime(2023, 1, 1), bank_account_number="12345678", bank_name="First National Bank of Utopia Republic", bank_swift_code="FNBU", bank_branch="Kingdom District", company=company)
# john.save()

john = models.Staff.objects.first()

# gross_pay: models.PayrollComponent = models.PayrollComponent(company=company, name="Gross Pay", description="Gross Pay", variable="gross_pay", component_type="input", order=0, formula=None, value=None, effective_from=datetime.datetime(2023, 1, 1))
# gross_pay.save()
# pension_benefit: models.PayrollComponent = models.PayrollComponent(company=company, name="Pension Benefit", description="Pension Benefit", variable="pension_benefit", component_type="input", order=1, formula=None, value=None, effective_from=datetime.datetime(2023, 1, 1))
# pension_benefit.save()
# personal_relief_monthly: models.PayrollComponent = models.PayrollComponent(company=company, name="Personal Relief Monthly", description="Personal Relief Monthly", variable="personal_relief_monthly", component_type="fixed", order=2, formula=None, value=2_400.00, effective_from=datetime.datetime(2023, 1, 1))
# personal_relief_monthly.save()
# nita: models.PayrollComponent = models.PayrollComponent(company=company, name="NITA", description="NITA", variable="nita", component_type="fixed", order=3, formula=None, value=50.00, effective_from=datetime.datetime(2023, 1, 1))
# nita.save()
# nssf_contribution_employee: models.PayrollComponent = models.PayrollComponent(company=company, name="NSSF Contribution", description="NSSF Contribution", variable="nssf_contribution_employee", component_type="formula", order=4, formula="calculate_nssf_contribution(gross_pay)", value=None, effective_from=datetime.datetime(2023, 1, 1))
# nssf_contribution_employee.save()
# affordable_housing_levy: models.PayrollComponent = models.PayrollComponent(company=company, name="Affordable Housing Levy", description="Affordable Housing Levy", variable="affordable_housing_levy", component_type="formula", order=5, formula="0.015 * gross_pay", value=None, effective_from=datetime.datetime(2023, 1, 1))
# affordable_housing_levy.save()
# affordable_housing_relief: models.PayrollComponent = models.PayrollComponent(company=company, name="Affordable Housing Relief", description="Affordable Housing Relief", variable="affordable_housing_relief", component_type="formula", order=6, formula="0.15 * affordable_housing_levy", value=None, effective_from=datetime.datetime(2023, 1, 1))
# affordable_housing_relief.save()
# shif_contribution: models.PayrollComponent = models.PayrollComponent(company=company, name="SHIF Contribution", description="SHIF Contribution", variable="shif_contribution", component_type="formula", order=7, formula="0.0275 * gross_pay", value=None, effective_from=datetime.datetime(2023, 1, 1))
# shif_contribution.save()
# deductable_shif_contribution: models.PayrollComponent = models.PayrollComponent(company=company, name="Deductable SHIF Contribution", description="Deductable SHIF Contribution", variable="deductable_shif_contribution", component_type="formula", order=8, formula="0.15 * shif_contribution", value=None, effective_from=datetime.datetime(2023, 1, 1))
# deductable_shif_contribution.save()
# taxable_income: models.PayrollComponent = models.PayrollComponent(company=company, name="Taxable Income", description="Taxable Income", variable="taxable_income", component_type="formula", order=9, formula="gross_pay + pension_benefit - nssf_contribution_employee", value=None, effective_from=datetime.datetime(2023, 1, 1))
# taxable_income.save()
# gross_paye: models.PayrollComponent = models.PayrollComponent(company=company, name="Gross PAYE", description="Gross PAYE", variable="gross_paye", component_type="formula", order=10, formula="calculate_paye(taxable_income)", value=None, effective_from=datetime.datetime(2023, 1, 1))
# gross_paye.save()
# net_paye: models.PayrollComponent = models.PayrollComponent(company=company, name="Net PAYE", description="Net PAYE", variable="net_paye", component_type="formula", order=11, formula="gross_paye - personal_relief_monthly - affordable_housing_relief", value=None, effective_from=datetime.datetime(2023, 1, 1))
# net_paye.save()
# affordable_housing_levy_employer: models.PayrollComponent = models.PayrollComponent(company=company, name="Affordable Housing Levy Employer", description="Affordable Housing Levy Employer", variable="affordable_housing_levy_employer", component_type="formula", order=12, formula="0.015 * gross_pay", value=None, effective_from=datetime.datetime(2023, 1, 1))
# affordable_housing_levy_employer.save()
# nssf_contribution_employer: models.PayrollComponent = models.PayrollComponent(company=company, name="NSSF Contribution Employer", description="NSSF Contribution Employer", variable="nssf_contribution_employer", component_type="formula", order=13, formula="calculate_nssf_contribution(gross_pay)", value=None, effective_from=datetime.datetime(2023, 1, 1))
# nssf_contribution_employer.save()
# total_deductions: models.PayrollComponent = models.PayrollComponent(company=company, name="Total Deductions", description="Total Deductions", variable="total_deductions", component_type="formula", order=14, formula="nssf_contribution_employee + net_paye + shif_contribution + affordable_housing_levy", value=None, effective_from=datetime.datetime(2023, 1, 1))
# total_deductions.save()
# net_pay: models.PayrollComponent = models.PayrollComponent(company=company, name="Net Pay", description="Net Pay", variable="net_pay", component_type="formula", order=15, formula="gross_pay - total_deductions", value=None, effective_from=datetime.datetime(2023, 1, 1))
# net_pay.save()

payroll_components = models.PayrollComponent.objects(company=company)

# computation: models.Computation = models.Computation(company=company, notes="Jan 2023 Payroll control", payroll_period_start=datetime.datetime(2023, 1, 1), payroll_period_end=datetime.datetime(2023, 1, 31))
# computation.save()

computation = models.Computation.objects.first()

compensation = {
    "gross_pay": 600_000.00,
    "pension_benefit": 0.00
}

# for ck, cv in compensation.items():
#     computation_component = models.ComputationComponent(computation=computation, payroll_component=payroll_components.get(variable=ck), staff=john, value=cv)
#     computation_component.save()

payroll_results: Dict[str, float] = {}
for staff, payroll in computation.run():
    print(f"{staff.first_name} {staff.last_name} Payroll")
    pprint.pprint(payroll)
    payroll_results: Dict[str, float] = payroll
    break

