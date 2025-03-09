import io
import secrets
from typing import Dict, List
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi import Depends
from fastapi.responses import FileResponse
import crud
import schemas
import models
from depends import get_db, authorize, get_query_params
from config import logger
import pandas as pd
import os
import bson

router = APIRouter(dependencies=[Depends(get_db)])

# Staff API
# TODO: Check if the user sending the request has the permission perform the action within the company
@router.post("/",
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
@router.get("/template",
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
async def download(file_path:str, _: models.User = Depends(authorize(perm="create_staff"))) -> FileResponse:
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",filename="Staff Template.xlsx")
    else:
        raise HTTPException(status_code=404,detail={"message":"No such file was found"})

# upload staff data to a given company
@router.post("/upload",
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
    
@router.get("/",
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

@router.get("/{staff_id}",
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

@router.put("/{staff_id}",
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
    
@router.delete("/{staff_id}",
            tags=["Staff"],
            status_code=204
        )
async def delete_staff(
            company_id: str,
            staff_id: str,
            _: models.User = Depends(authorize(perm="delete_staff"))
        ):
    try:
        company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
        staff = models.Staff.objects.filter(id=bson.ObjectId(staff_id),company=company_db).first()
        if not staff:
            raise HTTPException(status_code=404,detail={
                "message":"Staff not found in the company"
            })
        is_deleted = await crud.delete_obj(model=models.Staff, id=staff_id)
        if is_deleted:
            return None
        else:
            return {"message":"Something went wrong"},500
    except Exception as e:
        logger.error(f"Error deleting staff: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message": f"{e}"
        })
