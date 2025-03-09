from decimal import ROUND_HALF_UP, Decimal
import io
import json
from pprint import pprint
import secrets
from typing import Any, Dict, List
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi import Depends
from fastapi.responses import FileResponse, StreamingResponse
import mongoengine
import crud
import schemas
import models
from depends import get_db, authorize, get_query_params
from config import logger
import pandas as pd
import os
import bson

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
            "message":f"An unexpected {e} error occurred"
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
        print(company)
        company_db: models.Company = await crud.update_obj(model=models.Company, id=company_id, obj_in=company)
        return company_db.to_dict()
    except Exception as e:
        logger.error(f"Error updating company: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message": f"An unexpected error {e} occurred"
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
@router.post("/companies/{company_id}/staff",
            response_model=schemas.StaffInDB,
            tags=["Staff"],
            status_code=201
        )
async def create_staff(
            company_id: str,
            staff_create: schemas.StaffCreate,
            _: models.User = Depends(authorize(perm="create_staff")),
        ):
    try:
        company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
        user = await crud.get_obj_or_404(model=models.User, id=staff_create.user.id)
        if models.Staff.objects.filter(user=user).first():
            raise HTTPException(status_code=400,detail={
                "message":"User already has a staff account"
            })
        staff_db = await crud.create_staff(staff_create=staff_create, company=company_db)
        return staff_db.to_dict()
    except Exception as e:
        logger.error(f"Error creating staff: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message": f"{e}"
        })

# get staff template url
@router.get("/companies/{company_id}/get-staff-template",
            tags=["Staff"],
            status_code=200
        )
async def get_staff_template(
            company_id: str,
            _: models.User = Depends(authorize(perm="create_staff")),
            request: Request = None
        ):
    _ = await crud.get_obj_or_404(model=models.Company, id=company_id)
    staff_template_path = os.path.join("templates","Staff Template.xlsx")
    return {"url":f"{request.base_url}payroll/staff-template/{staff_template_path}"}

# download staff template
@router.get("/staff-template/{file_path:path}",status_code=200)
async def download(file_path:str, user: models.User = Depends(authorize(perm="create_staff"))) -> FileResponse:
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",filename="Staff Template.xlsx")
    else:
        raise HTTPException(status_code=404,detail={"message":"No such file was found"})

# upload staff data to a given company
@router.post("/companies/{company_id}/upload-staff",
            tags=["Staff"],
            status_code=200,
            response_model=List[schemas.StaffInDB]
        )
async def upload_staff(
            company_id: str,
            _: models.User = Depends(authorize(perm="create_staff")),
            file: UploadFile = File(...)
        ):
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents), sheet_name="Staff Template")
    # ensure that the file has at least 2 rows i.e at least one staff data
    if len(df) == 0:
        raise HTTPException(status_code=400,detail={"message":"No data found in the file"})
    # ensure no empty rows or columns
    if not df.isnull().values.any():
        raise HTTPException(status_code=400,detail={"message":"Empty rows or columns found in the file"})
    # ensure no users based on the email exist that already have staff accounts
    for idx in df.index:
        row = df.loc[idx]
        user = models.User.objects.filter(email=row['User Email']).first()
        if user and models.Staff.objects.filter(user=user).first():
            raise HTTPException(status_code=400,detail={
                "message":f"{idx} User with email {user.email} already has a staff account"
            })
    # loop through the rows and create staff objects where a user with 'User Email' does not exist, create one
    staff_list = []
    for idx in df.index:
        row = df.loc[idx]
        user = models.User.objects.filter(email=row['User Email']).first()
        if not user:
            user = models.User(
                email=row['User Email'],
                name=row['First Name'] + " " + row['Last Name'],
                is_active=False
            )
            # generate a random password for the user
            user.set_password(secrets.token_urlsafe(8))
            user.save()
            # TODO: send an email to the user to set their password      
        staff = models.Staff(
            user=user,
            company=company_db,
            first_name=row['First Name'],
            last_name=row['Last Name'],
            job_title=row['Job Title'],
            department=row['Department'],
            contact_email=row['Contact Email'],
            contact_phone=str(row['Contact Phone']),
            pin_number=row['PIN Number'],
            staff_number=row['Staff Number'],
            shif_number=row['SHIF Number'],
            nssf_number=row['NSSF Number'],
            nita_number=row['NITA Number'],
            national_id_number=str(row['National ID Number']),
            date_of_birth=row['Date of Birth'],
            is_active=row['Is Active'],
            joined_on=row['Joined On'],
            departed_on=row["Departed On"] if isinstance(row.get('Departed On'), str) else None,
            bank_account_number=str(row['Bank Account Number']),
            bank_name=row['Bank Name'],
            bank_swift_code=str(row['Bank Swift Code']),
            bank_branch=row['Bank Branch'],
        )
        staff.save()
        staff_list.append(staff)
    return [staff.to_dict() for staff in staff_list]
    
@router.get("/companies/{company_id}/staff",
            response_model=schemas.ListResponse,
            tags=["Staff"],
            status_code=200
        )
async def get_company_staff(
            company_id: str,
            params: Dict = Depends(get_query_params),
            _: models.User = Depends(authorize(perm="read_staff")),
        ) -> schemas.ListResponse:
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    params['company'] = company_db
    return await crud.paginate(model=models.Staff, schema=schemas.StaffInDB, **params)

@router.get("/companies/{company_id}/staff/{staff_id}",
            response_model=schemas.StaffInDB,
            tags=["Staff"],
            status_code=200
        )
async def get_staff(
            company_id: str,
            staff_id: str,
            _: models.User = Depends(authorize(perm="read_staff")),
        ):
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    staff_db = models.Staff.objects.filter(id=bson.ObjectId(staff_id),company=company_db).first()
    if not staff_db:
        raise HTTPException(status_code=404,detail={
            "message":"Staff not found in the company"
        })
    return staff_db.to_dict()

@router.put("/companies/{company_id}/staff/{staff_id}",
            response_model=schemas.StaffInDB,
            tags=["Staff"],
            status_code=200
        )
async def update_staff(
            company_id: str,
            staff_id: str,
            staff_create: schemas.StaffUpdate,
            _: models.User = Depends(authorize(perm="update_staff")),
        ):
    try:
        company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
        staff = models.Staff.objects.filter(id=bson.ObjectId(staff_id),company=company_db).first()
        if not staff:
            raise HTTPException(status_code=404,detail={
                "message":"Staff not found in the company"
            })
        staff_db: models.Staff = await crud.update_obj(model=models.Staff, id=staff_id, obj_in=staff_create)
        return staff_db.to_dict()
    except Exception as e:
        logger.error(f"Error updating staff: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message": f"{e}"
        })
    
@router.delete("/companies/{company_id}/staff/{staff_id}",
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
    except mongoengine.errors.NotUniqueError as e:
        logger.error(f"Error creating payroll code: {str(e)}")
        raise HTTPException(status_code=400,detail={
            "message":"Payroll code with the same variable name, order, company and effective_from already exists"
        })
    except Exception as e:
        logger.error(f"Error creating payroll code: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message": f"{e}"
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
    except mongoengine.errors.NotUniqueError as e:
        logger.error(f"Error creating payroll code: {str(e)}")
        raise HTTPException(status_code=400,detail={
            "message":"Payroll code with the same variable name, order, company and effective_from already exists"
        })
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
            "message": f"{e}"
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
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",filename="compensation.xlsx")
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