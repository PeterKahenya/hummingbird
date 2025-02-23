import os
import pdfkit
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

def format_currency(value):
    """Formats numbers as currency with two decimal places."""
    return f"{value:,.2f}"

def generate_payslip():
    # Generate payslip
    context = {
        "date_from": "2023-01-01 00:00:00",
        "date_to": "2023-01-31 00:00:00",
        "employee": {
            "name": "John Doe",
            "position": "Software Engineer",
            "email": "john.doe@acme.com",
            "phone": "12345678",
            "staff_id": "22113344"
        },
        "payslip_items": [
            {"item": "gross_pay", "description": "gross pay", "type": "gross pay", "amount": 600000.00},
            {"item": "pension_benefit", "description": "pension benefit", "type": "pension benefit", "amount": 0.00},
            {"item": "personal_relief_monthly", "description": "personal relief monthly", "type": "personal relief", "amount": 2400.00},
            {"item": "nita", "description": "nita", "type": "nita", "amount": 80.00},
            {"item": "nssf_employee", "description": "nssf contribution employee", "type": "nssf", "amount": 2160.00},
            {"item": "housing_levy", "description": "affordable housing levy", "type": "levy", "amount": 9000.00},
            {"item": "housing_relief", "description": "affordable housing relief", "type": "relief", "amount": 1350.00},
            {"item": "shif_contribution", "description": "shif contribution", "type": "shif", "amount": 16500.00},
            {"item": "deductable_shif", "description": "deductable shif contribution", "type": "deductable", "amount": 2475.00},
            {"item": "taxable_income", "description": "taxable income", "type": "taxable", "amount": 597840.00},
            {"item": "gross_paye", "description": "gross paye", "type": "gross paye", "amount": 176581.35},
            {"item": "net_paye", "description": "net paye", "type": "net paye", "amount": 172831.35},
            {"item": "housing_levy_employer", "description": "affordable housing levy employer", "type": "levy", "amount": 9000.00},
            {"item": "nssf_employer", "description": "nssf contribution employer", "type": "nssf", "amount": 2160.00},
        ],
        "total_earnings": 600000.00,
        "total_deductions": 200491.35,
        "net_pay": 399508.65
    }
    env = Environment(loader=FileSystemLoader("templates/master_org"))
    env.filters["format_currency"] = format_currency
    template = env.get_template("payslip1.html")
    payroll_html_string =  template.render(context)
    options = {
        'page-size': 'A4',
        'margin-top': '0mm',
        'margin-right': '0mm',
        'margin-bottom': '0mm',
        'margin-left': '0mm',
        'encoding': "UTF-8",
        'no-outline': None
    }
    config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
    pdfkit.from_string(payroll_html_string, "reports/master_org/sample_payslip.pdf", options=options, configuration=config)



generate_payslip()