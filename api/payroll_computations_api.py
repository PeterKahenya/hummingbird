from decimal import ROUND_HALF_UP, Decimal
import io
import json
from typing import Dict, List
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi import Depends
from fastapi.responses import FileResponse, StreamingResponse
import crud
import schemas
import models
from depends import get_db, authorize, get_query_params
from config import logger
import pandas as pd
import os
import bson

router = APIRouter(dependencies=[Depends(get_db)]) 

# Computation API
@router.post("/",
            response_model=schemas.ComputationInDB,
            tags=["Computations"],
            status_code=201
        )
async def create_computation(
        company_id: str,
        computation_create: schemas.ComputationCreate,
        _: models.User = Depends(authorize(perm="create_computations"))
    ):
    try:
        company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
        await crud.get_obj_or_404(model=models.User, id=str(computation_create.generated_by.id))
        computation_db = await crud.create_computation(computation_create=computation_create, company=company_db)
        return computation_db.to_dict()
    except Exception as e:
        logger.error(f"Error creating computation: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })

@router.get("/",
            response_model=schemas.ListResponse,
            tags=["Computations"],
            status_code=200
        )
async def get_computations(
            company_id: str,
            params: Dict = Depends(get_query_params),
            _: models.User = Depends(authorize(perm="read_computations"))
        ) -> schemas.ListResponse:
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    params['company'] = company_db
    return await crud.paginate(model=models.Computation, schema=schemas.ComputationInDB, **params)

@router.get("/{computation_id}",
            response_model=schemas.ComputationInDB,
            tags=["Computations"],
            status_code=200
        )
async def get_computation(
            company_id: str,
            computation_id: str,
            _: models.User = Depends(authorize(perm="read_computations"))
        ):
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    computation_db = models.Computation.objects.filter(id=bson.ObjectId(computation_id),company=company_db).first()
    if not computation_db:
        raise HTTPException(status_code=404,detail={
            "message":"Computation not found in the company"
        })
    return computation_db.to_dict()

@router.put("/{computation_id}",
            response_model=schemas.ComputationInDB,
            tags=["Computations"],
            status_code=200
        )
async def update_computation(
            company_id: str,
            computation_id: str,
            computation: schemas.ComputationUpdate,
            _: models.User = Depends(authorize(perm="update_computations"))
        ):
    try:
        company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
        computation_db = models.Computation.objects.filter(id=bson.ObjectId(computation_id),company=company_db).first()
        if not computation_db:
            raise HTTPException(status_code=404,detail={
                "message":"Computation not found in the company"
            })
        computation_db: models.Computation = await crud.update_obj(model=models.Computation, id=computation_id, obj_in=computation)
        return computation_db.to_dict()
    except Exception as e:
        logger.error(f"Error updating computation: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message": f"{e}"
        })
    
@router.delete("/{computation_id}",
            tags=["Computations"],
            status_code=204
        )
async def delete_computation(
        company_id: str,
        computation_id: str,
        _: models.User = Depends(authorize(perm="delete_computations"))
    ):
    try:
        company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
        computation_db = models.Computation.objects.filter(id=bson.ObjectId(computation_id),company=company_db).first()
        if not computation_db:
            raise HTTPException(status_code=404,detail={
                "message":"Computation not found in the company"
            })
        is_deleted = await crud.delete_obj(model=models.Computation, id=computation_id)
        if is_deleted:
            return None
        else:
            return {"message":"Something went wrong"},500
    except Exception as e:
        logger.error(f"Error deleting computation: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
# Other Computations API    
@router.get("/{computation_id}/compensation-template",
            tags=["Computations"],
            status_code=200
        )
async def get_compensations_template(
            company_id: str,
            computation_id: str,
            _: models.User = Depends(authorize(perm="read_computations")),
            request: Request = None
        ):
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    computation_db = models.Computation.objects.filter(id=bson.ObjectId(computation_id),company=company_db).first()
    if not computation_db:
        raise HTTPException(status_code=404,detail={
            "message":"Computation not found in the company"
        })
    payroll_codes = models.PayrollCode.objects.filter(
                    company=computation_db.company,
                    code_type="input",
                    effective_from__lte=computation_db.payroll_period_start,
                ).order_by("order")
    names = ['Staff Number']
    descriptions=['Contains the staff ID that the employer uses']
    variables = ['staff_number']
    for payroll_code in payroll_codes:
        names.append(payroll_code.name)
        descriptions.append(payroll_code.description)
        variables.append(payroll_code.variable)
    # create a excel file with the payroll codes for columns to be filled by the user
    # the excel file will be downloaded by the user
    company_home = os.path.join("templates",computation_db.company.name)
    template_dir = os.path.join(company_home,f"{payroll_codes[0].effective_from.strftime('%Y-%m')}")
    os.makedirs(template_dir,exist_ok=True)
    template_path = os.path.join(template_dir,"compensation.xlsx")
    df = pd.DataFrame(
        [
            names,
            descriptions
        ],
        columns=variables
    )
    df.to_excel(template_path,index=False)
    return {"url":f"{request.base_url}files/{template_path}"}

@router.post("/{computation_id}/upload-compensation",
            tags=["Computations"],
            status_code=200,
            response_model=List[schemas.ComputationComponentInDB]
        )
async def upload_compensation(
        company_id: str,
        computation_id: str,
        _: models.User = Depends(authorize(perm="read_computations")),
        file: UploadFile = File(...)
    ):
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    computation_db = models.Computation.objects.filter(id=bson.ObjectId(computation_id),company=company_db).first()
    if not computation_db:
        raise HTTPException(status_code=404,detail={
            "message":"Computation not found in the company"
        })
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))
    # ensure that the file has at least 3 rows i.e at least one staff data
    if len(df) <= 2:
        raise HTTPException(status_code=400,detail={"message":"No data found in the file"})
    # ensure that column headers are either staff_number or the payroll code variable
    if df.columns[0] !='staff_number':
        raise HTTPException(status_code=400,detail={"message":"Staff Number column is missing or is not the first one"})
    for col in df.columns[1:]:
        payroll_code = models.PayrollCode.objects.filter(
                                                    company=computation_db.company,
                                                    code_type="input",
                                                    effective_from__lte=computation_db.payroll_period_start,
                                                    variable=col).first()
        if not payroll_code:
            raise HTTPException(status_code=400,detail={"message":f"Payroll code with variable {col} not found"})
    # validate all staff numbers in the file
    for staff_number in df['staff_number'][2:]:
        staff = models.Staff.objects.filter(staff_number=staff_number,company=computation_db.company).first()
        if not staff:
            raise HTTPException(status_code=400,detail={"message":f"Staff with staff number {staff_number} not found in the company {computation_db.company.name}"})
    # create computation components for each staff
    for idx in df.index[2:]:
        row = df.loc[idx]
        staff = models.Staff.objects.filter(staff_number=row['staff_number'], company=computation_db.company).first()
        for col in df.columns[1:]:
            payroll_code = models.PayrollCode.objects.filter(
                                                    company=computation_db.company,
                                                    code_type="input",
                                                    effective_from__lte=computation_db.payroll_period_start,
                                                    variable=col).first()
            value = row[col]
            computation_component = models.ComputationComponent(
                computation=computation_db,
                payroll_component=payroll_code,
                staff=staff,
                value=value
            )
            computation_component.save()
    computation_components = models.ComputationComponent.objects.filter(computation=computation_db)
    return [comp.to_dict() for comp in computation_components]

# run computation
@router.post("/{computation_id}/run",
            tags=["Computations"],
            status_code=200,
            response_model=List[schemas.ComputationComponentInDB]
        )
async def run_computation(
    company_id: str,
    computation_id: str,
    _: models.User = Depends(authorize(perm="read_computations")),
):
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    computation_db = models.Computation.objects.filter(id=bson.ObjectId(computation_id),company=company_db).first()
    if not computation_db:
        raise HTTPException(status_code=404,detail={
            "message":"Computation not found in the company"
        })
    def convert_decimals(obj):
        """Recursively convert Decimal values to rounded float values in a nested structure."""
        if isinstance(obj, Decimal):
            return float(obj.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))  # Round to 2 decimal places
        elif isinstance(obj, dict):
            return {k: convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_decimals(v) for v in obj]
        return obj  # Return other types unchanged
    async def run():        
        for staff,params in computation_db.run():
            params.pop("__builtins__")
            params.pop("Decimal")
            params.pop("calculate_paye")
            params.pop("calculate_nssf_contribution")
            params = convert_decimals(params)
            yield json.dumps({
                "staff": {
                    "id": str(staff.id),
                    "staff_number": staff.staff_number,
                    "name": staff.full_name
                },
                "payroll": params
                }).encode() + b"\n"
    return StreamingResponse(content=run(),media_type="application/x-ndjson")