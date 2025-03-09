from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from fastapi import Depends
import crud
import schemas
import models
from depends import get_db, authorize, get_query_params
from config import logger

router = APIRouter(dependencies=[Depends(get_db)])

# Companies API
@router.post("/", 
            response_model=schemas.CompanyInDB, 
            tags=["Companies"], 
            status_code=201)
async def create_company(
            company: schemas.CompanyCreate, 
            _: models.User = Depends(authorize(perm="create_companies")),
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
    
@router.get("/",
            response_model=schemas.ListResponse,
            tags=["Companies"],
            status_code=200
        )
async def get_companies(
            params: Dict = Depends(get_query_params),
            _: models.User = Depends(authorize(perm="read_companies"))
        ) -> schemas.ListResponse:
    return await crud.paginate(model=models.Company, schema=schemas.CompanyInDB, **params)

@router.get("/{company_id}",
            response_model=schemas.CompanyInDB,
            tags=["Companies"],
            status_code=200
        )
async def get_company(
            company_id: str,
            _: models.User = Depends(authorize(perm="read_companies"))
        ):
    company_db = await crud.get_obj_or_404(model=models.Company, id=company_id)
    return company_db.to_dict()

@router.put("/{company_id}",
            response_model=schemas.CompanyInDB,
            tags=["Companies"],
            status_code=200
        )
async def update_company(
            company_id: str,
            company: schemas.CompanyUpdate,
            _: models.User = Depends(authorize(perm="update_companies"))
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
    
@router.delete("/{company_id}",
            tags=["Companies"],
            status_code=204
        )
async def delete_company(
            company_id: str,
            _: models.User = Depends(authorize(perm="delete_companies"))
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
