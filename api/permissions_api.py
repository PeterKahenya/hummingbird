from typing import Any, Dict
from fastapi import APIRouter, Depends
from depends import get_db, get_query_params, authorize
import crud
import models
import schemas

router = APIRouter(dependencies=[Depends(get_db)])

@router.get("/", status_code=200, tags=["Authorize"])
async def get_permissions(
                            params: Dict[str, Any] = Depends(get_query_params),
                            user: models.User = Depends(authorize(perm="read_permissions")),
                            db = Depends(get_db),
                        ) -> schemas.ListResponse:
    return await crud.paginate(model=models.Permission, schema=schemas.PermissionInDB, **params)

@router.get("/{permission_id}", status_code=200, tags=["Authorize"])
async def get_permission(
                            permission_id: str,
                            user: models.User = Depends(authorize(perm="read_permissions")),
                            db = Depends(get_db)
                        ) -> schemas.PermissionInDB:
    permission_db = await crud.get_obj_or_404(model=models.Permission,id=permission_id)
    return permission_db.to_dict()