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

gross_pay: float = 600000.0
pension_benefit: float = 00.00
nssf_contribution: float = 2_160.00
affordable_housing_levy: float = eval("0.015 * gross_pay")
affordable_housing_relief: float = eval("0.15 * affordable_housing_levy")
shif_contribution: float = eval("0.0275 * gross_pay")
deductable_shif_contribution: float = eval("0.15 * shif_contribution")
taxable_income: float = eval("gross_pay + pension_benefit - nssf_contribution")
gross_paye: float = eval("calculate_paye(taxable_income)")
personal_relief_monthly: float = 2_400.00
tax = eval("gross_paye - personal_relief_monthly - affordable_housing_relief")

pprint.pprint({
    "gross_pay": f"{gross_pay:,}",
    "pension_benefit": pension_benefit,
    "nssf_contribution": nssf_contribution,
    "affordable_housing_levy": f"{round(affordable_housing_levy,2):,}",
    "affordable_housing_relief": f"{round(affordable_housing_relief,2):,}",
    "shif_contribution": shif_contribution,
    "deductable_shif_contribution": deductable_shif_contribution,
    "taxable_income": taxable_income,
    "gross_paye": gross_paye,
    "personal_relief_monthly": personal_relief_monthly,
    "tax": tax
})