from fastapi import APIRouter, HTTPException
from fastapi import Depends
from fastapi.responses import FileResponse
import models
from depends import get_db, authorize
import os

router = APIRouter(dependencies=[Depends(get_db)]) 

# Files API
# TODO: Check if the user sending the request has the permission download this particular file, maybe have files like payslips, staff template, company report, p9a be objects in the database with urls to the files and permissions to download them
@router.get("/{file_path:path}",status_code=200)
async def download(file_path:str, _: models.User = Depends(authorize(perm="read_computations"))) -> FileResponse:
    if os.path.exists(file_path):
        file_type = file_path.split(".")[-1]
        file_name = file_path.split("/")[-1]
        if file_type == "pdf":
            return FileResponse(file_path, media_type="application/pdf",filename=file_name)
        elif file_type == "xlsx":
            return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",filename=file_name)
    else:
        raise HTTPException(status_code=404,detail={"message":"No such file was found"})