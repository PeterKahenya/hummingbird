import io
import json
from typing import Any, Dict, List
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

router = APIRouter(dependencies=[Depends(get_db)])

# Companies API

@router.post("/companies", 
            response_model=schemas.CompanyInDB, 
            tags=["Companies"], 
            status_code=201)
async def create_company(
            company: schemas.CompanyCreate, 
            user: models.User = Depends(authorize(perm="create_companies")),
            db: Any = Depends(get_db)
        ):
    try:
        company_db: models.Company = await crud.create_obj(model=models.Company, obj_in=company)
        company_db.clone_master_company()
        return company_db.to_dict()
    except Exception as e:
        logger.error(f"Error creating company: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.get("/companies",
            response_model=schemas.ListResponse,
            tags=["Companies"],
            status_code=200
        )
async def get_companies(
            params: Dict = Depends(get_query_params),
            user: models.User = Depends(authorize(perm="read_companies")),
            db: Any = Depends(get_db)
        ) -> schemas.ListResponse:
    return await crud.paginate(model=models.Company, schema=schemas.CompanyInDB, **params)

@router.get("/companies/{company_id}",
            response_model=schemas.CompanyInDB,
            tags=["Companies"],
            status_code=200
        )
async def get_company(
            company_id: str,
            user: models.User = Depends(authorize(perm="read_companies")),
            db: Any = Depends(get_db)
        ):
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    return company_db.to_dict()

@router.put("/companies/{company_id}",
            response_model=schemas.CompanyInDB,
            tags=["Companies"],
            status_code=200
        )
async def update_company(
            company_id: str,
            company: schemas.CompanyUpdate,
            user: models.User = Depends(authorize(perm="update_companies")),
            db: Any = Depends(get_db)
        ):
    try:
        company_db: models.Company = await crud.update_obj(model=models.Company, id=company_id, obj_in=company)
        return company_db.to_dict()
    except Exception as e:
        logger.error(f"Error updating company: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.delete("/companies/{company_id}",
            tags=["Companies"],
            status_code=204
        )
async def delete_company(
            company_id: str,
            user: models.User = Depends(authorize(perm="delete_companies")),
            db: Any = Depends(get_db)
        ):
    try:
        is_deleted = await crud.delete_obj(model=models.Company, id=company_id)
        if is_deleted:
            return None
        else:
            return {"message":"Something went wrong"},500
    except Exception as e:
        logger.error(f"Error deleting company: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
# Staff API
@router.post("/staff",
            response_model=schemas.StaffInDB,
            tags=["Staff"],
            status_code=201
        )
async def create_staff(
            staff: schemas.StaffCreate,
            user: models.User = Depends(authorize(perm="create_staff")),
            db: Any = Depends(get_db)
        ):
    try:
        staff_db = await crud.create_obj(model=models.Staff, obj_in=staff)
        return staff_db.to_dict()
    except Exception as e:
        logger.error(f"Error creating staff: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.get("/staff",
            response_model=schemas.ListResponse,
            tags=["Staff"],
            status_code=200
        )
async def get_staff(
            params: Dict = Depends(get_query_params),
            user: models.User = Depends(authorize(perm="read_staff")),
            db: Any = Depends(get_db)
        ) -> schemas.ListResponse:
    return await crud.paginate(model=models.Staff, schema=schemas.StaffInDB, **params)

@router.get("/staff/{staff_id}",
            response_model=schemas.StaffInDB,
            tags=["Staff"],
            status_code=200
        )
async def get_staff(
            staff_id: str,
            user: models.User = Depends(authorize(perm="read_staff")),
            db: Any = Depends(get_db)
        ):
    staff_db = await crud.get_obj_or_404(model=models.Staff, id=staff_id)
    return staff_db.to_dict()

@router.put("/staff/{staff_id}",
            response_model=schemas.StaffInDB,
            tags=["Staff"],
            status_code=200
        )
async def update_staff(
            staff_id: str,
            staff: schemas.StaffUpdate,
            user: models.User = Depends(authorize(perm="update_staff")),
            db: Any = Depends(get_db)
        ):
    try:
        staff_db: models.Staff = await crud.update_obj(model=models.Staff, id=staff_id, obj_in=staff)
        return staff_db.to_dict()
    except Exception as e:
        logger.error(f"Error updating staff: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.delete("/staff/{staff_id}",
            tags=["Staff"],
            status_code=204
        )
async def delete_staff(
            staff_id: str,
            user: models.User = Depends(authorize(perm="delete_staff")),
            db: Any = Depends(get_db)
        ):
    try:
        is_deleted = await crud.delete_obj(model=models.Staff, id=staff_id)
        if is_deleted:
            return None
        else:
            return {"message":"Something went wrong"},500
    except Exception as e:
        logger.error(f"Error deleting staff: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
# Payroll Bands API
@router.post("/bands",
            response_model=schemas.BandInDB,
            tags=["Bands"],
            status_code=201
        )
async def create_band(
            band: schemas.BandCreate,
            user: models.User = Depends(authorize(perm="create_bands")),
            db: Any = Depends(get_db)
        ):
    try:
        band_db = await crud.create_obj(model=models.Band, obj_in=band)
        return band_db.to_dict()
    except Exception as e:
        logger.error(f"Error creating band: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.get("/bands",
            response_model=schemas.ListResponse,
            tags=["Bands"],
            status_code=200
        )
async def get_bands(
            params: Dict = Depends(get_query_params),
            user: models.User = Depends(authorize(perm="read_bands")),
            db: Any = Depends(get_db)
        ) -> schemas.ListResponse:
    return await crud.paginate(model=models.Band, schema=schemas.BandInDB, **params)

@router.get("/bands/{band_id}",
            response_model=schemas.BandInDB,
            tags=["Bands"],
            status_code=200
        )
async def get_band(
            band_id: str,
            user: models.User = Depends(authorize(perm="read_bands")),
            db: Any = Depends(get_db)
        ):
    band_db = await crud.get_obj_or_404(model=models.Band, id=band_id)
    return band_db.to_dict()

@router.put("/bands/{band_id}",
            response_model=schemas.BandInDB,
            tags=["Bands"],
            status_code=200
        )
async def update_band(
            band_id: str,
            band: schemas.BandUpdate,
            user: models.User = Depends(authorize(perm="update_bands")),
            db: Any = Depends(get_db)
        ):
    try:
        band_db: models.Band = await crud.update_obj(model=models.Band, id=band_id, obj_in=band)
        return band_db.to_dict()
    except Exception as e:
        logger.error(f"Error updating band: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.delete("/bands/{band_id}",
            tags=["Bands"],
            status_code=204
        )
async def delete_band(
            band_id: str,
            user: models.User = Depends(authorize(perm="delete_bands")),
            db: Any = Depends(get_db)
        ):
    try:
        is_deleted = await crud.delete_obj(model=models.Band, id=band_id)
        if is_deleted:
            return None
        else:
            return {"message":"Something went wrong"},500
    except Exception as e:
        logger.error(f"Error deleting band: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    

# Payroll Codes API
@router.post("/codes",
            response_model=schemas.PayrollCodeInDB,
            tags=["Payroll Codes"],
            status_code=201
        )
async def create_payroll_code(
            code: schemas.PayrollCodeCreate,
            user: models.User = Depends(authorize(perm="create_payrollcodes")),
            db: Any = Depends(get_db)
        ):
    try:
        code_db = await crud.create_obj(model=models.PayrollCode, obj_in=code)
        return code_db.to_dict()
    except Exception as e:
        logger.error(f"Error creating payroll code: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.get("/codes",
            response_model=schemas.ListResponse,
            tags=["Payroll Codes"],
            status_code=200
        )
async def get_payroll_codes(
            params: Dict = Depends(get_query_params),
            user: models.User = Depends(authorize(perm="read_payrollcodes")),
            db: Any = Depends(get_db)
        ) -> schemas.ListResponse:
    return await crud.paginate(model=models.PayrollCode, schema=schemas.PayrollCodeInDB, **params)

@router.get("/codes/{code_id}",
            response_model=schemas.PayrollCodeInDB,
            tags=["Payroll Codes"],
            status_code=200
        )
async def get_payroll_code(
            code_id: str,
            user: models.User = Depends(authorize(perm="read_payrollcodes")),
            db: Any = Depends(get_db)
        ):
    code_db = await crud.get_obj_or_404(model=models.PayrollCode, id=code_id)
    return code_db.to_dict()

@router.put("/codes/{code_id}",
            response_model=schemas.PayrollCodeInDB,
            tags=["Payroll Codes"],
            status_code=200
        )
async def update_payroll_code(
            code_id: str,
            code: schemas.PayrollCodeUpdate,
            user: models.User = Depends(authorize(perm="update_payrollcodes")),
            db: Any = Depends(get_db)
        ):
    try:
        code_db: models.PayrollCode = await crud.update_obj(model=models.PayrollCode, id=code_id, obj_in=code)
        return code_db.to_dict()
    except Exception as e:
        logger.error(f"Error updating payroll code: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.delete("/codes/{code_id}",
            tags=["Payroll Codes"],
            status_code=204
        )
async def delete_payroll_code(
            code_id: str,
            user: models.User = Depends(authorize(perm="delete_payrollcodes")),
            db: Any = Depends(get_db)
        ):
    try:
        is_deleted = await crud.delete_obj(model=models.PayrollCode, id=code_id)
        if is_deleted:
            return None
        else:
            return {"message":"Something went wrong"},500
    except Exception as e:
        logger.error(f"Error deleting payroll code: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })

# Computation API
@router.post("/computations",
            response_model=schemas.ComputationInDB,
            tags=["Computations"],
            status_code=201
        )
async def create_computation(
            computation: schemas.ComputationCreate,
            user: models.User = Depends(authorize(perm="create_computations")),
            db: Any = Depends(get_db)
        ):
    try:
        computation_db = await crud.create_obj(model=models.Computation, obj_in=computation)
        return computation_db.to_dict()
    except Exception as e:
        logger.error(f"Error creating computation: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })

@router.get("/computations",
            response_model=schemas.ListResponse,
            tags=["Computations"],
            status_code=200
        )
async def get_computations(
            params: Dict = Depends(get_query_params),
            user: models.User = Depends(authorize(perm="read_computations")),
            db: Any = Depends(get_db)
        ) -> schemas.ListResponse:
    return await crud.paginate(model=models.Computation, schema=schemas.ComputationInDB, **params)

@router.get("/computations/{computation_id}",
            response_model=schemas.ComputationInDB,
            tags=["Computations"],
            status_code=200
        )
async def get_computation(
            computation_id: str,
            user: models.User = Depends(authorize(perm="read_computations")),
            db: Any = Depends(get_db)
        ):
    computation_db = await crud.get_obj_or_404(model=models.Computation, id=computation_id)
    return computation_db.to_dict()

@router.put("/computations/{computation_id}",
            response_model=schemas.ComputationInDB,
            tags=["Computations"],
            status_code=200
        )
async def update_computation(
            computation_id: str,
            computation: schemas.ComputationUpdate,
            user: models.User = Depends(authorize(perm="update_computations")),
            db: Any = Depends(get_db)
        ):
    try:
        computation_db: models.Computation = await crud.update_obj(model=models.Computation, id=computation_id, obj_in=computation)
        return computation_db.to_dict()
    except Exception as e:
        logger.error(f"Error updating computation: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.delete("/computations/{computation_id}",
            tags=["Computations"],
            status_code=204
        )
async def delete_computation(
            computation_id: str,
            user: models.User = Depends(authorize(perm="delete_computations")),
            db: Any = Depends(get_db)
        ):
    try:
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
@router.get("/computations/{computation_id}/compensation-template",
            tags=["Computations"],
            status_code=200
        )
async def get_compensations_template(
            computation_id: str,
            user: models.User = Depends(authorize(perm="read_computations")),
            db: Any = Depends(get_db),
            request: Request = None
        ):
    computation_db = await crud.get_obj_or_404(model=models.Computation, id=computation_id)
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
    return {"url":f"{request.base_url}payroll/files/{template_path}"}

@router.get("/files/{file_path:path}",status_code=200)
async def download(file_path:str, user: models.User = Depends(authorize(perm="read_computations"))) -> FileResponse:
    # print(f"Trying to download {file_path}")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404,detail={"message":"No such file was found"})

@router.post("/computations/{computation_id}/upload-compensation",
            tags=["Computations"],
            status_code=200,
            response_model=List[schemas.ComputationComponentInDB]
        )
async def upload_compensation(
    computation_id: str,
    user: models.User = Depends(authorize(perm="read_computations")),
    file: UploadFile = File(...)
):
    computation_db = await crud.get_obj_or_404(model=models.Computation, id=computation_id)
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
        staff = models.Staff.objects.filter(staff_number=row['staff_number']).first()
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
@router.post("/computations/{computation_id}/run",
            tags=["Computations"],
            status_code=200,
            response_model=List[schemas.ComputationComponentInDB]
        )
async def run_computation(
    computation_id: str,
    user: models.User = Depends(authorize(perm="read_computations")),
    db: Any = Depends(get_db)
):
    computation_db = await crud.get_obj_or_404(model=models.Computation, id=computation_id)
    async def run():
        for staff,params in computation_db.run():
            yield json.dumps({
                "staff":schemas.StaffInDB.model_validate(staff.to_dict()).model_dump_json(),
                "payroll":params}).encode() + b"\n"
    
    return StreamingResponse(content=run(),media_type="application/x-ndjson")