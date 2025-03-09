from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Form
from depends import get_db, email_password_authenticate, get_app
from config import settings, logger
import models
import schemas
import utils

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
    if not user:
        raise HTTPException(status_code=404,detail={"message":"User not found"})
    if not await user.validate_verification_code(code,mode="phone"):
        raise HTTPException(status_code=400,detail={"message":"Invalid verification code"})
    user.save()
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
    utils.mailtrap_send_email(to=(user.email,user.name),subject="Hummingbird Email Verification Code",message=message)
    return {"message":"Email verification code sent", "success":True, "email":user.email}

@router.post("/verify-email/verify",status_code=200,tags=["Authenticate"])
async def verify_email_verify(email: str = Form(...), code: str = Form(...), db = Depends(get_db), app: models.ClientApp = Depends(get_app)) -> Dict[str,Any]:
    user: models.User = models.User.objects.filter(email=email).first()
    if not user:
        raise HTTPException(status_code=404,detail={"message":"User not found"})
    if not await user.validate_verification_code(code,mode="email"):
        raise HTTPException(status_code=400,detail={"message":"Invalid verification code"})
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