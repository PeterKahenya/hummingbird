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
from api.apps_api import Dict, HTTPException
import crud
import schemas
import models
from depends import get_db
import os
import collections
from openpyxl import Workbook, load_workbook
import utils

router = APIRouter(dependencies=[Depends(get_db)])
    
# Generate company payroll report
@router.post("/generate", 
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
        "url": f"{request.base_url}files/{report_path}"
    }