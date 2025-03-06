from typing import Annotated, Any, Dict, Optional
from fastapi import Depends, Form, HTTPException, Query, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, OAuth2PasswordBearer
from mongoengine import connect, disconnect
import config
from config import logger
import crud
import models
import schemas

class HummingbirdOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request=None, websocket: WebSocket=None) -> Optional[HTTPAuthorizationCredentials]:
        request = request or websocket
        if not request:
            if self.auto_error:
                raise HTTPException(status_code= status.HTTP_403_FORBIDDEN,detail="Not authenticated")
            return None
        return await super().__call__(request)

oauth2_scheme = HummingbirdOAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_db():
    """Initialize MongoDB connection."""
    try:
        connect(
            host=config.DB_URL
        )
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise e
    finally:
        disconnect()
        
async def get_app(client_id: Annotated[str, Form()], client_secret: Annotated[str, Form()], db = Depends(get_db)) -> models.ClientApp:
    clientapp = models.ClientApp.objects.filter(client_id=client_id,client_secret=client_secret).first()
    if not clientapp:
        raise HTTPException(status_code=401,detail={"message":"Client credentials are invalid"})
    return clientapp

async def email_password_authenticate(email: Annotated[str, Form()], password: Annotated[str, Form()], client_id: Annotated[str, Form()], client_secret: Annotated[str, Form()], db = Depends(get_db)) -> models.User:
    user = models.User.objects.filter(email=email).first()
    if not user:
        raise HTTPException(status_code=404,detail={"message":"User not found"})
    if not user.check_password(password):
        raise HTTPException(status_code=401,detail={"message":"Invalid password"})
    return user

async def authenticate(access_token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> models.User:
    email,client_id,client_secret = models.User.verify_jwt_token(access_token,config.settings.jwt_secret_key,config.settings.jwt_algorithm)
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
    user = models.User.objects.filter(email=email).first()
    if not user:
        logger.error(f"User with email: {email} not found")
        raise HTTPException(status_code=401, detail={"message":"Invalid access token"})
    if not user.is_active:
        logger.error(f"User with email: {email} is not active")
        raise HTTPException(status_code=401, detail={"message":"User is not active"})
    if not user.is_verified:
        logger.error(f"User with email: {email} is not verified")
        raise HTTPException(status_code=401, detail={"message":"User is not verified"})
    return user

async def check_permission(perm: str, user: models.User) -> models.User:
    if await user.has_perm(perm):
        return user
    else:
        raise HTTPException(status_code=403,detail={"message":"User not authorized to view this object or perform this action"})

def authorize(perm: str):
    async def _authorize(user: models.User = Depends(authenticate), db = Depends(get_db)) -> models.User:
        return await check_permission(perm, user)
    return _authorize

async def get_query_params(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    q: Optional[str] = None,
) -> Dict[str, Any]:
    query_params = dict(request.query_params)
    query_params.pop('page', None)
    query_params.pop('size', None)
    query_params.pop('q', None)
    params = {
        "page": page,
        "size": size,
        "q": q,
        **query_params
    }
    return params