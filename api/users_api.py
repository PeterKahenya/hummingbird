from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from fastapi import Depends
import crud
import schemas
import models
from depends import get_db, authorize, get_query_params
from config import logger

router = APIRouter(dependencies=[Depends(get_db)])
    
@router.get("/me",status_code=200,tags=["Profile"])
async def me(user: models.User = Depends(authorize(perm="read_users"))) -> schemas.UserInDB:
    return user.to_dict()

@router.post("/", status_code=201, tags=["Authorize"])
async def create_user(
                        user_create: schemas.UserCreate,
                        user: models.User = Depends(authorize(perm="create_users")),
                        db = Depends(get_db)
                    ) -> schemas.UserInDB:
    try:
        user_db: models.User = await crud.create_obj(model=models.User,obj_in=user_create)
        return user_db.to_dict()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
    
@router.get("/", status_code=200, tags=["Authorize"])
async def get_users(
                        params: Dict[str, Any] = Depends(get_query_params),
                        user: models.User = Depends(authorize(perm="read_users")),
                        db = Depends(get_db)
                    ) -> schemas.ListResponse:
    return await crud.paginate(
                                model=models.User,
                                schema=schemas.UserInDB,
                                **params
                            )

# get user by id
@router.get("/{user_id}", status_code=200, tags=["Authorize"])
async def get_user(
                        user_id: str,
                        user: models.User = Depends(authorize(perm="read_users")),
                        db = Depends(get_db)
                    ) -> schemas.UserInDB:
    user_db = await crud.get_obj_or_404(model=models.User,id=user_id)
    return user_db.to_dict()

# update user
@router.put("/{user_id}", status_code=200, tags=["Authorize"])
async def update_user(
                        user_id: str,
                        user_update: schemas.UserUpdate,
                        user: models.User = Depends(authorize(perm="update_users")),
                        db = Depends(get_db)
                    ) -> schemas.UserInDB:
    try:
        user_db: models.User = await crud.update_obj(model=models.User,id=user_id,obj_in=user_update)
        return user_db.to_dict()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":f"An unexpected error: {e} occurred"
        })
    
# delete user
@router.delete("/{user_id}", status_code=204, tags=["Authorize"])
async def delete_user(
                        user_id: str,
                        user: models.User = Depends(authorize(perm="delete_users")),
                        db = Depends(get_db)
                    ) -> None:
    try:
        is_deleted = await crud.delete_obj(model=models.User,id=user_id)
        if is_deleted:
            return None
        else:
            return {"message":"Something went wrong"},500
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":f"An unexpected error {e} occurred"
        })