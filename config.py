from pydantic_settings import BaseSettings
import logging
from honeybadger.contrib.logger import HoneybadgerHandler

class AppSettings(BaseSettings):
    mongodb_user: str = "test"
    mongodb_password: str = "test"
    mongodb_host: str = "localhost"
    mongodb_port: str = "27017"
    mongodb_database: str = "test"
    honeybadger_api_key: str = "honeybadger_api_key"
    jwt_secret_key: str = "c6e5"
    jwt_algorithm: str = "HS256"
    access_token_expiry_minutes: int = 30
    verification_code_length: int = 6
    verification_code_expiry_seconds: int = 300
    mailtrap_api_token: str = "f7b1"
    smsleopard_base_url: str = "https://smsleopard.com/api/v1"
    smsleopard_api_key: str = "smsleopard_api_key"
    smsleopard_api_secret: str = "sms"
    superuser_email: str = "test@test.com"
    superuser_phone: str = "254700000000"
    superuser_password: str = "password"

settings = AppSettings()

DB_URL = f"mongodb://{settings.mongodb_user}:{settings.mongodb_password}@{settings.mongodb_host}:{settings.mongodb_port}/{settings.mongodb_database}"
DEFAULT_CONTENT_CLASSES = ["users", "roles", "permissions", "contenttypes", "clientapps", "bands", "companies", "staff", "payrollcodes", "computations", "computationcomponents"]
DEFAULT_PERMISSIONS_CLASSES = ["create","read","update","delete"]

hb_handler = HoneybadgerHandler(api_key=settings.honeybadger_api_key)
hb_handler.setLevel(logging.DEBUG)
hb_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger('honeybadger')
logger.addHandler(hb_handler)