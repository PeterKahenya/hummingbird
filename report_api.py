import datetime
import json
from typing import List, Optional
from urllib import request
import bson
from fastapi import APIRouter, Request
from fastapi import Depends
from fastapi.responses import FileResponse, StreamingResponse
from jinja2 import Environment, FileSystemLoader
from mongoengine import Q
import pdfkit
from pytest import File
from auth_api import Dict, HTTPException
import crud
import schemas
import models
from depends import get_db
import os
import collections
from openpyxl import Workbook, load_workbook
from pypdf import PdfReader, PdfWriter

router = APIRouter(dependencies=[Depends(get_db)])

def add_password_to_pdf(input_pdf, output_pdf, password):
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    # Copy all pages to the new PDF
    for page in reader.pages:
        writer.add_page(page)

    # Encrypt with password
    writer.encrypt(password)

    # Save the protected PDF
    with open(output_pdf, "wb") as f:
        writer.write(f)

def format_currency(value):
    """Formats numbers as currency with two decimal places."""
    return f"{float(value):,.2f}" if value else "0.00"

def generate_payslip(computation_db: models.Computation, staff_db: models.Staff):
    # Generate payslip
    net_pay_code = models.PayrollCode.objects.filter(company=computation_db.company, variable="net_pay").first()
    computation_components = models.ComputationComponent.objects.filter(computation=computation_db, staff=staff_db).order_by("payroll_component__order").all()
    net_pay_component = models.ComputationComponent.objects.filter(computation=computation_db, staff=staff_db, payroll_component=net_pay_code).first()
    context = {
        "date_from": computation_db.payroll_period_start.strftime("%Y-%m-%d %H:%M:%S"),
        "date_to": computation_db.payroll_period_end.strftime("%Y-%m-%d %H:%M:%S"),
        "employee": {
            "name": staff_db.full_name,
            "position": staff_db.job_title,
            "email": staff_db.contact_email,
            "phone": staff_db.contact_phone,
            "staff_number": staff_db.staff_number,
        },
        "payslip_items": [
            {
                "name": computation_component.payroll_component.name,
                "description": computation_component.payroll_component.description,
                "type": computation_component.payroll_component.code_type,
                "value": computation_component.value,
                "tags": computation_component.payroll_component.tags,
            }
            for computation_component in computation_components
        ],
        "total_earnings": sum([computation_component.value for computation_component in computation_components if "COMP" in computation_component.payroll_component.tags]),
        "total_deductions": sum([computation_component.value for computation_component in computation_components if "DED" in computation_component.payroll_component.tags]),
        "net_pay": net_pay_component.value,
        "company": {
            "name": computation_db.company.name,
            "address": computation_db.company.address,
            "email": computation_db.company.contact_email,
            "phone": computation_db.company.contact_phone,
            "pin_number": computation_db.company.pin_number,
        },
    }
    env = Environment(loader=FileSystemLoader(f"templates/{computation_db.company.name}"))
    env.filters["format_currency"] = format_currency
    template = env.get_template("payslip.html")
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
    computation_start_date = computation_db.payroll_period_start.strftime("%Y-%m-%d")
    payslips_dir = f"reports/{computation_db.company.name}/{computation_start_date}/payslips"
    os.makedirs(payslips_dir, exist_ok=True)
    payslip_path = f"{payslips_dir}/{staff_db.full_name +'-'+str(staff_db.id)}.pdf"
    pdfkit.from_string(payroll_html_string, payslip_path, options=options, configuration=config)
    add_password_to_pdf(payslip_path, payslip_path, staff_db.date_of_birth.strftime("%Y%m%d"))
    return payslip_path

def generate_p9a(computations: Dict[int, models.Computation|None], staff_db: models.Staff, company_db: models.Company, period_start: datetime.datetime, period_end: datetime.datetime):
    computation_components = {}
    totals = collections.defaultdict(float)
    for month, computation_db in computations.items():
        if computation_db:
            all_components = models.ComputationComponent.objects.filter(computation=computation_db, staff=staff_db).order_by("payroll_component__order").all()
            computation_components[month] = {component.payroll_component.variable:component.value for component in all_components }
            for component in all_components:
                totals[component.payroll_component.variable] += float(component.value)
        else:
            computation_components[month] = None
    context = {
        "date_from": period_start,
        "date_to": period_end,
        "employee": {
            "name": staff_db.full_name,
            "position": staff_db.job_title,
            "pin_number": staff_db.pin_number,
            "email": staff_db.contact_email,
            "phone": staff_db.contact_phone,
            "staff_number": staff_db.staff_number,
        },
        "monthly_payroll": computation_components,
        "totals": totals,
        "company": company_db.to_dict(),
    }
    env = Environment(loader=FileSystemLoader(f"templates/{company_db.name}"))
    env.filters["format_currency"] = format_currency
    template = env.get_template("p9a.html")
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
    period = period_start.strftime("%Y")
    payslips_dir = f"reports/{company_db.name}/{period}/p9as"
    os.makedirs(payslips_dir, exist_ok=True)
    p9a_path = f"{payslips_dir}/{staff_db.full_name +'-'+str(staff_db.id)}.pdf"
    pdfkit.from_string(payroll_html_string, p9a_path, options=options, configuration=config)
    add_password_to_pdf(p9a_path, p9a_path, staff_db.date_of_birth.strftime("%Y%m%d"))
    return p9a_path

# Generate payslips
@router.post("/companies/{company_id}/computations/{computation_id}/generate-payslips", 
            tags=["Reports"],
            status_code=200,
            response_model=List[schemas.ComputationComponentInDB]
        )
async def generate_payslips(
    company_id: str,
    computation_id: str, 
    request: Request, db=Depends(get_db)):
    """
    Generate payslips for each staff in a computation
    """
    company_db = await crud.get_obj_or_404(models.Company, company_id)
    computation_db = models.Computation.objects.filter(company=company_db, id=bson.ObjectId(computation_id)).first()
    if not computation_db:
        raise HTTPException(status_code=404,detail={"message":"No such computation was found"})
    staff = models.Staff.objects.filter(company=computation_db.company).all()
    async def generate():
        for staff_db in staff:
            payslip_path = generate_payslip(computation_db, staff_db)
            yield json.dumps({
                "staff":schemas.StaffInDB.model_validate(staff_db.to_dict()).model_dump_json(),
                "payslip_url": f"{request.base_url}reports/files/{payslip_path}"
            }).encode() + b"\n"
    return StreamingResponse(generate(), media_type="application/x-ndjson")

# Download payslip
@router.get("/files/{payslip_path:path}", 
            tags=["Reports"],
            status_code=200
        )
async def download_payslip(
    payslip_path: str
):
    """
    Download payslip
    """
    if os.path.exists(payslip_path):
        return FileResponse(payslip_path, media_type="application/pdf")
    else:
        raise HTTPException(status_code=404,detail={"message":"No such file was found"})
    
# Generate p9as
@router.post("/companies/{company_id}/generate-p9as", 
            tags=["Reports"],
            status_code=200,
        )
async def generate_p9as(
                        company_id: str, 
                        period_start: datetime.datetime = None,
                        period_end: datetime.datetime = None,
                        request:Request = None,
                    ):
    """
        Generate P9As each staff in a computation
    """
    company_db = await crud.get_obj_or_404(models.Company, company_id)
    qualifying_staff = models.Staff.objects.filter(
        Q(company=company_db) & (Q(departed_on=None) | Q(departed_on__gte=period_start))
    )
    async def generate():
        for staff_db in qualifying_staff:
            # loop through all the months of the year
            computations = {}
            for month in range(1, 13):
                month_start = datetime.datetime(period_start.year, month, 1)
                month_end = datetime.datetime(period_start.year, month + 1, 1) if month < 12 else datetime.datetime(period_start.year + 1, 1, 1)
                computation_db = models.Computation.objects.filter(
                    Q(company=company_db) &
                    Q(payroll_period_start__gte=month_start) &
                    Q(payroll_period_start__lt=month_end)
                ).first()
                computations[month_start.strftime("%B")] = computation_db if computation_db else None
            p9a_path = generate_p9a(
                computations=computations,
                staff_db=staff_db,
                company_db=company_db,
                period_start=period_start,
                period_end=period_end
            )
            yield json.dumps({
                "staff":schemas.StaffInDB.model_validate(staff_db.to_dict()).model_dump_json(),
                "p9a_url": f"{request.base_url}reports/files/{p9a_path}"
            }).encode() + b"\n"
    return StreamingResponse(generate(), media_type="application/x-ndjson")
    
# Download p9a
@router.get("/files/{p9a_path:path}", 
            tags=["Reports"],
            status_code=200
        )
async def download_p9a(
    p9a_path: str
):
    """
    Download P9A
    """
    if os.path.exists(p9a_path):
        return FileResponse(p9a_path, media_type="application/pdf")
    else:
        raise HTTPException(status_code=404,detail={"message":"No such file was found"})
    
# Generate company payroll report
@router.post("/companies/{company_id}/computations/{computation_id}/generate-payroll-report", 
            tags=["Reports"],
            status_code=200,
        )
async def generate_payroll_report(
                        company_id: str,
                        computation_id: str,
                        request:Request = None,
                    ):
    """
        Generate company payroll report for a computation using openpyxl to pupulate the following template sheets
        1. Company
        2. Staff
        3. Payroll Codes
        4. Computation
        5. Computation Data
    """
    company_db = await crud.get_obj_or_404(models.Company, company_id)
    computation_db = models.Computation.objects.filter(company=company_db, id=bson.ObjectId(computation_id)).first()
    if not computation_db:
        raise HTTPException(status_code=404,detail={"message":"No such computation was found"})
    company_db = await crud.get_obj_or_404(models.Company, computation_db.company.id)
    staff = models.Staff.objects.filter(company=computation_db.company).all()
    payroll_codes = models.PayrollCode.objects.filter(company=computation_db.company, effective_from__lte=computation_db.payroll_period_start).order_by("variable").all()
    template_path = f"templates/{computation_db.company.name}/Payroll Company Summary Template.xlsx"
    report_dir = f"reports/{computation_db.company.name}/{computation_db.payroll_period_start.strftime('%Y-%m-%d')}/summaries"
    os.makedirs(report_dir, exist_ok=True)
    report_path = f"{report_dir}/Payroll Company Summary.xlsx"
    workbook: Workbook = load_workbook(template_path)
    company_sheet = workbook["Company"]
    staff_sheet = workbook["Staff"]
    payroll_codes_sheet = workbook["Payroll Codes"]
    computation_sheet = workbook["Computation"]
    computation_data_sheet = workbook["Computation Data"]
    # populate company sheet
    for key, value in company_db.to_dict().items():
        value = value if value else ""
        company_sheet.append([key, value])
    # populate staff sheet
    staff_sheet.append([column.replace("_"," ").title() for column in staff[0].to_dict().keys()])
    for staff_db in staff:
        staff_details_list = []
        for value in staff_db.to_dict().values():
            if isinstance(value, dict):
                value = value["id"]
            staff_details_list.append(value)
        staff_sheet.append(staff_details_list)
    # populate payroll codes sheet
    payroll_codes_sheet.append(["Variable", "Description", "Formula", "Value", "Code Type", "Order", "Tags", "Effective From"])
    for payroll_code in payroll_codes:
        payroll_code_list = [payroll_code.variable, payroll_code.description, payroll_code.formula, payroll_code.value, payroll_code.code_type, payroll_code.order, "".join(payroll_code.tags), payroll_code.effective_from.strftime("%Y-%m-%d")]
        payroll_codes_sheet.append(payroll_code_list)
    # populate computation sheet
    for key, value in computation_db.to_dict().items():
        value = value if value else ""
        value = value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime.datetime) else value
        value = "" if isinstance(value, list) else value
        value = "" if isinstance(value, dict) else value
        computation_sheet.append([key, value])
    # populate computation data sheet
    computation_components = models.ComputationComponent.objects.filter(computation=computation_db).order_by("payroll_component__order").all()
    computation_data_sheet.append(["Staff ID"]+[code.payroll_component.name for code in computation_components])
    for staff_db in staff:
        staff_components = models.ComputationComponent.objects.filter(computation=computation_db, staff=staff_db).order_by("payroll_component__order").all()
        staff_component_values = [staff_db.staff_number] + [component.value for component in staff_components]
        computation_data_sheet.append(staff_component_values)
    workbook.save(report_path)
    return {
        "url": f"{request.base_url}reports/download/{report_path}"
    }

# Download company payroll report
@router.get("/download/{report_path:path}", 
            tags=["Reports"],
            status_code=200
        )
async def download_payroll_report(
    report_path: str
):
    """
        Download company payroll report
    """
    if os.path.exists(report_path):
        return FileResponse(report_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        raise HTTPException(status_code=404,detail={"message":"No such file was found"})