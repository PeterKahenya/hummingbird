from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from fastapi import Depends
import crud
import schemas
import models
from depends import get_db, authorize, get_query_params
from config import logger

router = APIRouter(dependencies=[Depends(get_db)])

@router.post("/", status_code=201, tags=["Authorize"])
async def create_app(
                        app_create: schemas.ClientAppCreate,
                        user: models.User = Depends(authorize(perm="create_clientapps")),
                        db = Depends(get_db)
                    ) -> schemas.ClientAppInDB:
    try:
        app_db: models.ClientApp = await crud.create_obj(model=models.ClientApp,obj_in=app_create)
        return app_db.to_dict()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    

@router.get("/", status_code=200, tags=["Authorize"])
async def get_apps(
                        params: Dict[str, Any] = Depends(get_query_params),
                        user: models.User = Depends(authorize(perm="read_clientapps")),
                        db = Depends(get_db)
                    ) -> schemas.ListResponse:
    return await crud.paginate(
                                model=models.ClientApp,
                                schema=schemas.ClientAppInDB,
                                **params
                            )

# get app by id
@router.get("/{app_id}", status_code=200, tags=["Authorize"])
async def get_app(
                        app_id: str,
                        user: models.User = Depends(authorize(perm="read_clientapps")),
                        db = Depends(get_db)
                    ) -> schemas.ClientAppInDB:
    app_db = await crud.get_obj_or_404(model=models.ClientApp,id=app_id)
    return app_db.to_dict()

# update app
@router.put("/{app_id}", status_code=200, tags=["Authorize"])
async def update_app(
                        app_id: str,
                        app_update: schemas.ClientAppUpdate,
                        user: models.User = Depends(authorize(perm="update_clientapps")),
                        db = Depends(get_db)
                    ) -> schemas.ClientAppInDB:
    try:
        print(app_update)
        app_db: models.ClientApp = await crud.update_obj(model=models.ClientApp,id=app_id,obj_in=app_update)
        print(app_db)
        return app_db.to_dict()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":f"An unexpected error: {e} occurred"
        })
    
# delete app
@router.delete("/{app_id}", status_code=204, tags=["Authorize"])
async def delete_app(
                        app_id: str,
                        user: models.User = Depends(authorize(perm="delete_clientapps")),
                        db = Depends(get_db)
                    ) -> None:
    try:
        is_deleted = await crud.delete_obj(model=models.ClientApp,id=app_id)
        if is_deleted:
            return None
        else:
            return {"message":"Something went wrong"},500
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":f"An unexpected error {e} occurred"
        })