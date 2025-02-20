from typing import Dict, List
import pprint


"""
Effective 1st July 2023

Monthly Pay Bands (Ksh.)            Annual Pay Bands (Ksh.)             Rate of Tax (%)

On the first kShs. 24,000           On the first KShs. 288,000          10
On the next KShs. 8,333             On the next KShs.100,000            25
On the next KShs. 467,667           On the next KShs. 5,612,000         30
On the next KShs. 300,000           On the next KShs. 3,600,00          32.5
On all income above KShs. 800,000   On all income above KShs. 9,600,000 35

"""
# PAYE bands
paye_bands_monthly: List[Dict[float, float]] = [
   {
        "lower": 0.00,
        "upper": 24_000.00,
        "rate": 10.00
    },
    {
        "lower": 24_000.00,
        "upper": 32_333.00,
        "rate": 25.00
    },
    {
        "lower": 32_333.00,
        "upper": 500_000.00,
        "rate": 30.00
    },
    {
        "lower": 500_000.00,
        "upper": 800_000.00,
        "rate": 32.50
    },
    {
        "lower": 800_000.00,
        "upper": float("inf"),
        "rate": 35.00
    }
]

# NSSF bands
nssf_bands: List[Dict[float, float]] = [
    {
        "lower": 0.00,
        "upper": 7_000.00,
        "rate": 6.00
    },
    {
        "lower": 7_000.00,
        "upper": 36_000.00,
        "rate": 6.00
    }
]

class Company:
    def __init__(self):
        self.name: str
        self.email: str
        self.phone: str
        self.pin: str
        self.paye_number: str
        self.nssf_number: str
        self.nhif_number: str
        self.logo: str

class Staff:
    def __init__(self):
        self.first_name: str
        self.last_name: str
        self.email: str
        self.phone: str
        self.national_id: str
        self.date_of_birth: str
        self.company: Company

class PayrollComputation:
    def __init__(self):
        self.company: str
        self.payroll_period_start: str
        self.payroll_period_end: str
        self.staff: List[Staff]
        self.payroll_computation_components: List[PayrollComputationComponent]
        


class PayrollComponent:
    def __init__(self, company: Company, name: str, description: str, variable: str, pctype: str, value: float = -1, formula: str = "", order: int = 0):
        assert pctype in ["input", "fixed", "formula"], "Invalid payroll component type, must be either 'input', 'fixed' or 'formula'"
        assert order >= 0
        if pctype == "fixed":
            assert value >= 0, "Invalid value for fixed payroll component"
        if pctype == "formula":
            assert formula != "", "Invalid formula for formula payroll component"
        if pctype == "input":
            assert value == -1, "Invalid value for input payroll component, must be -1"
        self.company: Company = company
        self.name: str = name
        self.description: str = description
        self.variable: str = name.lower().replace(" ", "_") if variable == "" else variable
        self.type: str = pctype # input, fixed, formula
        self.value: float = value # only applicable for fixed
        self.formula: str = formula # only applicable for formula
        self.order: int = order # order of computation

    def __str__(self):
        return f"{self.name}"
    
class PayrollComputationComponent:
    def __init__(self, payroll_component: PayrollComponent, staff: Staff, payroll_computation: PayrollComputation, value: float = -1):
        self.staff: Staff = staff
        self.payroll_computation: PayrollComputation = payroll_computation
        self.payroll_component: PayrollComponent = payroll_component
        if self.payroll_component.type == "input":
            assert value > -1, "Invalid value for input payroll component"
            self.value: float = value
        if self.payroll_component.type == "fixed":
            self.value: float = self.payroll_component.value
        

    def calculate(self, params: Dict[str, float] = {}):
        """
            Calculate the value of the payroll component
        """
        if self.payroll_component.type == "formula":
            self.value: float = eval(self.payroll_component.formula, globals(), params)
        return self.value
    
# predefined formulae  
def calculate_paye(taxable_income: float) -> float:
    """
        Calculate PAYE based on the taxable income and the PAYE bands
    """
    paye: float = 0.00
    for band in paye_bands_monthly:
        if taxable_income > band["upper"]:
            paye += (band["upper"] - band["lower"]) * (band["rate"] / 100)
        else:
            paye += (taxable_income - band["lower"]) * (band["rate"] / 100)
            break
    return paye

def calculate_nssf_contribution(gross_pay: float) -> float:
    """
        Calculate NSSF contribution based on the gross pay and the NSSF bands
    """
    nssf_contribution: float = 0.00
    for band in nssf_bands:
        if gross_pay > band["upper"]:
            nssf_contribution += (band["upper"] - band["lower"]) * band["rate"] / 100
        else:
            nssf_contribution += (gross_pay - band["lower"]) * band["rate"] / 100
            break
    return nssf_contribution


company: Company = Company()
company.name = "ACME Ltd"
company.email = "acme@acme.org"
company.phone = "0712345678"
company.pin = "P051234567A"
company.paye_number = "P051234567A"
company.nssf_number = "N051234567A"
company.nhif_number = "NH051234567A"
company.logo = "https://acme.org/logo.png"

john: Staff = Staff()
john.first_name = "John"
john.last_name = "Doe"
john.email = "john.doe@acme.org"
john.phone = "0712345678"
john.national_id = "12345678"
john.date_of_birth = "01/01/1990"
john.company = company

# payroll components
gross_pay: PayrollComponent = PayrollComponent(company, "Gross Pay", "Gross Pay", "gross_pay", "input", -1, "", 0)
pension_benefit: PayrollComponent = PayrollComponent(company, "Pension Benefit", "Pension Benefit", "pension_benefit", "input", -1, "", 1)
personal_relief_monthly: PayrollComponent = PayrollComponent(company, "Personal Relief Monthly", "Personal Relief Monthly", "personal_relief_monthly", "fixed", 2_400.00, "", 2)
nita: PayrollComponent = PayrollComponent(company, "NITA", "NITA", "nita", "fixed", 50.00, "", 3)
nssf_contribution_employee: PayrollComponent = PayrollComponent(company, "NSSF Contribution", "NSSF Contribution", "nssf_contribution_employee", "formula", -1, "calculate_nssf_contribution(gross_pay)", 4)
affordable_housing_levy: PayrollComponent = PayrollComponent(company, "Affordable Housing Levy", "Affordable Housing Levy", "affordable_housing_levy", "formula", -1, "0.015 * gross_pay", 5)
affordable_housing_relief: PayrollComponent = PayrollComponent(company, "Affordable Housing Relief", "Affordable Housing Relief", "affordable_housing_relief", "formula", -1, "0.15 * affordable_housing_levy", 6)
shif_contribution: PayrollComponent = PayrollComponent(company, "SHIF Contribution", "SHIF Contribution", "shif_contribution", "formula", -1, "0.0275 * gross_pay", 7)
deductable_shif_contribution: PayrollComponent = PayrollComponent(company, "Deductable SHIF Contribution", "Deductable SHIF Contribution", "deductable_shif_contribution", "formula", -1, "0.15 * shif_contribution", 8)
taxable_income: PayrollComponent = PayrollComponent(company, "Taxable Income", "Taxable Income", "taxable_income", "formula", -1, "gross_pay + pension_benefit - nssf_contribution_employee", 9)
gross_paye: PayrollComponent = PayrollComponent(company, "Gross PAYE", "Gross PAYE","gross_paye", "formula", -1, "calculate_paye(taxable_income)", 10)
net_paye: PayrollComponent = PayrollComponent(company, "Net PAYE", "Net PAYE", "net_paye", "formula", -1, "gross_paye - personal_relief_monthly - affordable_housing_relief", 11)
affordable_housing_levy_employer: PayrollComponent = PayrollComponent(company, "Affordable Housing Levy Employer", "Affordable Housing Levy Employer", "affordable_housing_levy_employer", "formula", -1, "0.015 * gross_pay", 12)
nssf_contribution_employer: PayrollComponent = PayrollComponent(company, "NSSF Contribution Employer", "NSSF Contribution Employer", "nssf_contribution_employer", "formula", -1, "calculate_nssf_contribution(gross_pay)", 13)
total_deductions: PayrollComponent = PayrollComponent(company, "Total Deductions", "Total Deductions", "total_deductions", "formula", -1, "nssf_contribution_employee + net_paye + shif_contribution + affordable_housing_levy", 14)
net_pay: PayrollComponent = PayrollComponent(company, "Net Pay", "Net Pay", "net_pay", "formula", -1, "gross_pay - total_deductions", 15)


# payroll computation
payroll_computation: PayrollComputation = PayrollComputation()
payroll_computation.company = company
payroll_computation.payroll_period_start = "01/01/2023"
payroll_computation.payroll_period_end = "31/01/2023"
payroll_computation.staff = [john]

# payroll computation components
john_payroll_computation_components: List[PayrollComputationComponent] = [
    PayrollComputationComponent(gross_pay, john, payroll_computation, 600_000.00),
    PayrollComputationComponent(pension_benefit, john, payroll_computation, 0.00),
    PayrollComputationComponent(personal_relief_monthly, john, payroll_computation, 2_400.00),
    PayrollComputationComponent(nita, john, payroll_computation),
    PayrollComputationComponent(nssf_contribution_employee, john, payroll_computation),
    PayrollComputationComponent(affordable_housing_levy, john, payroll_computation),
    PayrollComputationComponent(affordable_housing_relief, john, payroll_computation),
    PayrollComputationComponent(shif_contribution, john, payroll_computation),
    PayrollComputationComponent(deductable_shif_contribution, john, payroll_computation),
    PayrollComputationComponent(taxable_income, john, payroll_computation),
    PayrollComputationComponent(gross_paye, john, payroll_computation),
    PayrollComputationComponent(net_paye, john, payroll_computation),
    PayrollComputationComponent(affordable_housing_levy_employer, john, payroll_computation),
    PayrollComputationComponent(nssf_contribution_employer, john, payroll_computation),
    PayrollComputationComponent(total_deductions, john, payroll_computation),
    PayrollComputationComponent(net_pay, john, payroll_computation)
]

def run_payroll(payroll_computation: PayrollComputation):
    sorted_john_payroll_computation_components = sorted(john_payroll_computation_components, key=lambda x: x.payroll_component.order)
    params = {}
    for comp_component in sorted_john_payroll_computation_components:
        params[comp_component.payroll_component.variable] = comp_component.calculate(params)
        # print(f"{comp_component.payroll_component.variable}: {comp_component.value}")
    return params

payroll_results = run_payroll(payroll_computation)
