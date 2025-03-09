from typing import Dict
from fastapi import APIRouter, HTTPException
from fastapi import Depends
import mongoengine
import crud
import schemas
import models
from depends import get_db, authorize, get_query_params
from config import logger
import bson

router = APIRouter(dependencies=[Depends(get_db)]) 

# Payroll Codes API
# TODO: Check if the user sending the request has the permission perform the action within the company
@router.post("/",
            response_model=schemas.PayrollCodeInDB,
            tags=["Payroll Codes"],
            status_code=201
        )
async def create_payroll_code(
            company_id: str,
            code_create: schemas.PayrollCodeCreate,
            _: models.User = Depends(authorize(perm="create_payrollcodes"))
        ):
    try:
        company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
        code_db = await crud.create_code(code_create=code_create, company=company_db)
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
    
@router.get("/",
            response_model=schemas.ListResponse,
            tags=["Payroll Codes"],
            status_code=200
        )
async def get_payroll_codes(
            company_id: str,
            params: Dict = Depends(get_query_params),
            _: models.User = Depends(authorize(perm="read_payrollcodes"))
        ) -> schemas.ListResponse:
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    params['company'] = company_db
    return await crud.paginate(model=models.PayrollCode, schema=schemas.PayrollCodeInDB, **params)

@router.get("/{code_id}",
            response_model=schemas.PayrollCodeInDB,
            tags=["Payroll Codes"],
            status_code=200
        )
async def get_payroll_code(
            company_id: str,
            code_id: str,
            _: models.User = Depends(authorize(perm="read_payrollcodes"))
        ):
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    code_db = models.PayrollCode.objects.filter(id=bson.ObjectId(code_id),company=company_db).first()
    if not code_db:
        raise HTTPException(status_code=404,detail={
            "message":"Payroll code not found in the company"
        })
    return code_db.to_dict()

@router.put("/{code_id}",
            response_model=schemas.PayrollCodeInDB,
            tags=["Payroll Codes"],
            status_code=200
        )
async def update_payroll_code(
            company_id: str,
            code_id: str,
            code_update: schemas.PayrollCodeUpdate,
            _: models.User = Depends(authorize(perm="update_payrollcodes"))
        ):
    try:
        company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
        code = models.PayrollCode.objects.filter(id=bson.ObjectId(code_id),company=company_db).first()
        if not code:
            raise HTTPException(status_code=404,detail={
                "message":"Payroll code not found in the company"
            })
        code_db: models.PayrollCode = await crud.update_obj(model=models.PayrollCode, id=code_id, obj_in=code_update)
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
    
@router.delete("/{code_id}",
            tags=["Payroll Codes"],
            status_code=204
        )
async def delete_payroll_code(
            company_id: str,
            code_id: str,
            _: models.User = Depends(authorize(perm="delete_payrollcodes"))
        ):
    try:
        company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
        code = models.PayrollCode.objects.filter(id=bson.ObjectId(code_id),company=company_db).first()
        if not code:
            raise HTTPException(status_code=404,detail={
                "message":"Payroll code not found in the company"
            })
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
