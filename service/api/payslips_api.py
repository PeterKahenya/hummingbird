import json
from typing import List
import bson
from fastapi import APIRouter, Request
from fastapi import Depends
from fastapi.responses import FileResponse, StreamingResponse
from jinja2 import Environment, FileSystemLoader
import pdfkit
from api.apps_api import HTTPException
import crud
import schemas
import models
from depends import get_db
import os
import utils

router = APIRouter(dependencies=[Depends(get_db)])

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
    utils.add_password_to_pdf(payslip_path, payslip_path, staff_db.date_of_birth.strftime("%Y%m%d"))
    return payslip_path

# Generate payslips API
@router.post("/generate", 
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
                "payslip_url": f"{request.base_url}files/{payslip_path}"
            }).encode() + b"\n"
    return StreamingResponse(generate(), media_type="application/x-ndjson")