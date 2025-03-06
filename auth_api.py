from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from fastapi import Depends
import crud
import schemas
import models
from depends import get_db, email_password_authenticate, get_app, authorize, get_query_params
from config import logger,settings
import utils
from fastapi import Form

router = APIRouter(dependencies=[Depends(get_db)])

@router.post("/login",status_code=200,tags=["Authenticate"])
async def login(db = Depends(get_db), user: models.User = Depends(email_password_authenticate), app: models.ClientApp = Depends(get_app)) -> schemas.AccessToken:
    try:
        access_token = user.create_jwt_token(app, settings.jwt_secret_key,settings.jwt_algorithm,settings.access_token_expiry_minutes)
        chatter_role = models.Role.objects.filter(name="Chatter").first()
        if chatter_role not in user.roles and chatter_role:
            user.roles.append(chatter_role)  # by default a user is a chatter
        user.save()
        return schemas.AccessToken(access_token=access_token,token_type="Bearer",expires_in=settings.access_token_expiry_minutes*60)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={"message":"An unexpected error occurred"})
    
@router.post("/verify-phone/request",status_code=200,tags=["Authenticate"])
async def verify_phone_request(phone: str = Form(...), db = Depends(get_db), app: models.ClientApp = Depends(get_app)) -> Dict[str,Any]:
    user: models.User = models.User.objects.filter(phone=phone).first()
    if not user:
        raise HTTPException(status_code=404,detail={"message":"User not found"})
    user = await user.create_verification_code(
            code_length=settings.verification_code_length, 
            code_expiry_seconds=settings.verification_code_expiry_seconds,
            mode="phone"
        )
    message = f"Your hummingbird verification code is {user.phone_verification_code} please enter it to verify your phone number"
    await utils.smsleopard_send_sms(phone=user.phone, message=message)
    return {"message":"SMS verification code sent", "success":True, "phone":user.phone}

@router.post("/verify-phone/verify",status_code=200,tags=["Authenticate"])
async def verify_phone_verify(phone: str = Form(...), code: str = Form(...), db = Depends(get_db), app: models.ClientApp = Depends(get_app)) -> Dict[str,Any]:
    user: models.User = models.User.objects.filter(phone=phone).first()
    print
    if not user:
        raise HTTPException(status_code=404,detail={"message":"User not found"})
    if not await user.validate_verification_code(code,mode="phone"):
        raise HTTPException(status_code=400,detail={"message":"Invalid verification code"})
    return {"message":"Phone verified", "success":True, "phone":user.phone}

@router.post("/verify-email/request",status_code=200,tags=["Authenticate"])
async def verify_email_request(email: str = Form(...), db = Depends(get_db), app: models.ClientApp = Depends(get_app)) -> Dict[str,Any]:
    user: models.User = models.User.objects.filter(email=email).first()
    if not user:
        raise HTTPException(status_code=404,detail={"message":"User not found"})
    user = await user.create_verification_code(
            code_length=settings.verification_code_length, 
            code_expiry_seconds=settings.verification_code_expiry_seconds,
            mode="email"
        )
    message = f"Your hummingbird verification code is {user.email_verification_code} please enter it to verify your email"
    await utils.mailtrap_send_email(to=(user.email,user.name),subject="Hummingbird Email Verification Code",message=message)
    return {"message":"Email verification code sent", "success":True, "email":user.email}

@router.post("/verify-email/verify",status_code=200,tags=["Authenticate"])
async def verify_email_verify(email: str = Form(...), code: str = Form(...), db = Depends(get_db), app: models.ClientApp = Depends(get_app)) -> Dict[str,Any]:
    user: models.User = models.User.objects.filter(email=email).first()
    if not user:
        raise HTTPException(status_code=404,detail={"message":"User not found"})
    if not await user.validate_verification_code(code,mode="email"):
        raise HTTPException(status_code=400,detail={"message":"Invalid verification code"})
    user.is_verified = True
    user.save()
    return {"message":"Email verified", "success":True, "email":user.email}

@router.post("/refresh",status_code=200,tags=["Authenticate"])
async def refresh(access_token: str = Form(...), db = Depends(get_db), app: models.ClientApp = Depends(get_app)) -> schemas.AccessToken:
    try:
        email,client_id,client_secret = models.User.verify_jwt_token(access_token,settings.jwt_secret_key,settings.jwt_algorithm)
        if not email:
            logger.error("No email sub in token")
            raise HTTPException(status_code=401, detail={"message":"Invalid access token"})
        if not client_id or not client_secret:
            logger.error("No client_id or client_secret in token")
            raise HTTPException(status_code=401, detail={"message":"Invalid access token"})
        app = models.ClientApp.objects.filter(client_id=client_id,client_secret=client_secret).first()
        if not app:
            logger.error("Client not found")
            raise HTTPException(status_code=401, detail={"message":"Invalid access token"})
        user: models.User = models.User.objects.filter(email=email).first()
        if not user:
            logger.error(f"User with email: {email} not found")
            raise HTTPException(status_code=401, detail={"message":"Invalid access token"})
        if not user.is_active:
            logger.error(f"User with email: {email} is not active")
            raise HTTPException(status_code=401, detail={"message":"User is not active"})
        if not user.is_verified:
            logger.error(f"User with email: {email} is not verified")
            raise HTTPException(status_code=401, detail={"message":"User is not verified"})
        access_token = user.create_jwt_token(app, settings.jwt_secret_key,settings.jwt_algorithm,settings.access_token_expiry_minutes)
        return schemas.AccessToken(access_token=access_token,token_type="Bearer",expires_in=settings.access_token_expiry_minutes*60)
    except HTTPException as e:
        logger.warning(f"Error: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":"An unexpected error occurred",
        })
    
@router.get("/me",status_code=200,tags=["Profile"])
async def me(user: models.User = Depends(authorize(perm="read_users"))) -> schemas.UserInDB:
    return user.to_dict()

@router.get("/permissions/", status_code=200, tags=["Authorize"])
async def get_permissions(
                            params: Dict[str, Any] = Depends(get_query_params),
                            user: models.User = Depends(authorize(perm="read_permissions")),
                            db = Depends(get_db),
                        ) -> schemas.ListResponse:
    return await crud.paginate(model=models.Permission, schema=schemas.PermissionInDB, **params)

@router.get("/permissions/{permission_id}", status_code=200, tags=["Authorize"])
async def get_permission(
                            permission_id: str,
                            user: models.User = Depends(authorize(perm="read_permissions")),
                            db = Depends(get_db)
                        ) -> schemas.PermissionInDB:
    permission_db = await crud.get_obj_or_404(model=models.Permission,id=permission_id)
    return permission_db.to_dict()

@router.post("/roles/", status_code=201, tags=["Authorize"])
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
        
@router.get("/roles/", status_code=200, tags=["Authorize"])
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
@router.get("/roles/{role_id}", status_code=200, tags=["Authorize"])
async def get_role(
                        role_id: str,
                        user: models.User = Depends(authorize(perm="read_roles")),
                        db = Depends(get_db)
                    ) -> schemas.RoleInDB:
    role_db = await crud.get_obj_or_404(model=models.Role,id=role_id)
    return role_db.to_dict()

# update role
@router.put("/roles/{role_id}", status_code=200, tags=["Authorize"])
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
@router.delete("/roles/{role_id}", status_code=204, tags=["Authorize"])
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

@router.post("/users/", status_code=201, tags=["Authorize"])
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
    
@router.get("/users/", status_code=200, tags=["Authorize"])
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
@router.get("/users/{user_id}", status_code=200, tags=["Authorize"])
async def get_user(
                        user_id: str,
                        user: models.User = Depends(authorize(perm="read_users")),
                        db = Depends(get_db)
                    ) -> schemas.UserInDB:
    user_db = await crud.get_obj_or_404(model=models.User,id=user_id)
    return user_db.to_dict()

# update user
@router.put("/users/{user_id}", status_code=200, tags=["Authorize"])
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
@router.delete("/users/{user_id}", status_code=204, tags=["Authorize"])
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
    
# apps

@router.post("/apps/", status_code=201, tags=["Authorize"])
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
    

@router.get("/apps/", status_code=200, tags=["Authorize"])
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
@router.get("/apps/{app_id}", status_code=200, tags=["Authorize"])
async def get_app(
                        app_id: str,
                        user: models.User = Depends(authorize(perm="read_clientapps")),
                        db = Depends(get_db)
                    ) -> schemas.ClientAppInDB:
    app_db = await crud.get_obj_or_404(model=models.ClientApp,id=app_id)
    return app_db.to_dict()

# update app
@router.put("/apps/{app_id}", status_code=200, tags=["Authorize"])
async def update_app(
                        app_id: str,
                        app_update: schemas.ClientAppUpdate,
                        user: models.User = Depends(authorize(perm="update_clientapps")),
                        db = Depends(get_db)
                    ) -> schemas.ClientAppInDB:
    try:
        app_db: models.ClientApp = await crud.update_obj(model=models.ClientApp,id=app_id,obj_in=app_update)
        return app_db.to_dict()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500,detail={
            "message":f"An unexpected error: {e} occurred"
        })
    
# delete app
@router.delete("/apps/{app_id}", status_code=204, tags=["Authorize"])
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