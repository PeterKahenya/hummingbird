from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from depends import get_db, authorize, get_query_params
import crud
from config import logger
import models
import schemas

router = APIRouter(dependencies=[Depends(get_db)])

@router.post("/", status_code=201, tags=["Authorize"])
async def create_role(
                        role_create: schemas.RoleCreate,
                        user: models.User = Depends(authorize(perm="create_roles")),
                        db = Depends(get_db)
                    ) -> schemas.RoleInDB:
    try:
        role_db: models.Role = await crud.create_obj(model=models.Role,obj_in=role_create)
        return role_db.to_dict()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred"
        })
        
@router.get("/", status_code=200, tags=["Authorize"])
async def get_roles(
                        params: Dict[str, Any] = Depends(get_query_params),
                        user: models.User = Depends(authorize(perm="read_roles")),
                        db = Depends(get_db)
                    ) -> schemas.ListResponse:
    return await crud.paginate(
                                model=models.Role,
                                schema=schemas.RoleInDB,
                                **params
                            )

# get role by id
@router.get("/{role_id}", status_code=200, tags=["Authorize"])
async def get_role(
                        role_id: str,
                        user: models.User = Depends(authorize(perm="read_roles")),
                        db = Depends(get_db)
                    ) -> schemas.RoleInDB:
    role_db = await crud.get_obj_or_404(model=models.Role,id=role_id)
    return role_db.to_dict()

# update role
@router.put("/{role_id}", status_code=200, tags=["Authorize"])
async def update_role(
                        role_id: str,
                        role_update: schemas.RoleUpdate,
                        user: models.User = Depends(authorize(perm="update_roles")),
                        db = Depends(get_db)
                    ) -> schemas.RoleInDB:
    try:
        role_db: models.Role = await crud.update_obj(model=models.Role,id=role_id,obj_in=role_update)
        return role_db.to_dict()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":f"An unexpected error: {e} occurred"
        })
        
# delete role
@router.delete("/{role_id}", status_code=204, tags=["Authorize"])
async def delete_role(
                        role_id: str,
                        user: models.User = Depends(authorize(perm="delete_roles")),
                        db = Depends(get_db)
                    ) -> None:
    try:
        is_deleted = await crud.delete_obj(model=models.Role,id=role_id)
        if is_deleted:
            return None
        else:
            return {"message":"Something went wrong"},500
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":f"An unexpected error {e} occurred"
        })
