from typing import Dict
from fastapi import APIRouter, HTTPException
from fastapi import Depends
import crud
import schemas
import models
from depends import get_db, authorize, get_query_params
from config import logger

router = APIRouter(dependencies=[Depends(get_db)])

# Payroll Bands API
@router.post("/",
            response_model=schemas.BandInDB,
            tags=["Bands"],
            status_code=201
        )
async def create_band(
            band: schemas.BandCreate,
            _: models.User = Depends(authorize(perm="create_bands")),
        ):
    try:
        band_db = await crud.create_obj(model=models.Band, obj_in=band)
        return band_db.to_dict()
    except Exception as e:
        logger.error(f"Error creating band: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.get("/",
            response_model=schemas.ListResponse,
            tags=["Bands"],
            status_code=200
        )
async def get_bands(
            params: Dict = Depends(get_query_params),
            _: models.User = Depends(authorize(perm="read_bands"))
        ) -> schemas.ListResponse:
    return await crud.paginate(model=models.Band, schema=schemas.BandInDB, **params)

@router.get("/{band_id}",
            response_model=schemas.BandInDB,
            tags=["Bands"],
            status_code=200
        )
async def get_band(
            band_id: str,
            _: models.User = Depends(authorize(perm="read_bands"))
        ):
    band_db = await crud.get_obj_or_404(model=models.Band, id=band_id)
    return band_db.to_dict()

@router.put("/{band_id}",
            response_model=schemas.BandInDB,
            tags=["Bands"],
            status_code=200
        )
async def update_band(
            band_id: str,
            band: schemas.BandUpdate,
            _: models.User = Depends(authorize(perm="update_bands"))
        ):
    try:
        band_db: models.Band = await crud.update_obj(model=models.Band, id=band_id, obj_in=band)
        return band_db.to_dict()
    except Exception as e:
        logger.error(f"Error updating band: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.delete("/{band_id}",
            tags=["Bands"],
            status_code=204
        )
async def delete_band(
            band_id: str,
            _: models.User = Depends(authorize(perm="delete_bands"))
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
 