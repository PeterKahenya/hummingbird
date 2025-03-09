import datetime
import json
from fastapi import APIRouter, Request
from fastapi import Depends
from fastapi.responses import FileResponse, StreamingResponse
from jinja2 import Environment, FileSystemLoader
from mongoengine import Q
import pdfkit
from api.apps_api import Dict, HTTPException
import crud
import schemas
import models
from depends import get_db
import os
import collections
import utils

router = APIRouter(dependencies=[Depends(get_db)])

def format_currency(value):
    """Formats numbers as currency with two decimal places."""
    return f"{float(value):,.2f}" if value else "0.00"

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
    utils.add_password_to_pdf(p9a_path, p9a_path, staff_db.date_of_birth.strftime("%Y%m%d"))
    return p9a_path

# Generate p9as
@router.post("/generate", 
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
                "p9a_url": f"{request.base_url}files/{p9a_path}"
            }).encode() + b"\n"
    return StreamingResponse(generate(), media_type="application/x-ndjson")