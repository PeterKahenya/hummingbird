from decimal import Decimal
from openpyxl import formula
from pydantic import BaseModel,UUID4
from typing import Any, List,Optional
from datetime import datetime
from bson import ObjectId
from decimal import Decimal

class ListResponse(BaseModel):
    total: int
    page: int
    size: int
    data: List[Any]

class ModelBase(BaseModel):
    id: str
    
class ModelInDBBase(ModelBase):
    created_at: datetime
    updated_at: datetime | None

    model_config = {
        "from_attributes": True
    }

class ContentTypeInDB(ModelInDBBase):
    model: str
    object_id: str
    type_of_content: str

class PermissionCreate(BaseModel):
    content_type: ModelInDBBase
    codename: str
    name: str

class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    codename: Optional[str] = None
    content_type: Optional[ModelBase] = None

class PermissionInDB(ModelInDBBase):
    name: str
    codename: str
    content_type: ModelInDBBase

class RoleCreate(BaseModel):
    name: str
    description: str
    permissions: List[ModelInDBBase] | None = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: List[ModelBase] | None = []

class RoleInDB(ModelInDBBase):
    name: str
    permissions: List[PermissionInDB] | None = []

class UserCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = False
    is_verified: Optional[bool] = False
    phone_verification_code: Optional[str] = None
    last_seen: Optional[datetime] = None
    roles: Optional[List[ModelBase]] = []
    
class UserInDB(ModelInDBBase):
    name: str
    email: str
    phone: str
    is_active: bool
    is_verified: bool
    phone_verification_code: str | None
    phone_verification_code_expiry: datetime | None
    last_seen: datetime | None
    roles: List[RoleInDB] = []
    client_apps: List[ModelBase] = []

class UserVerify(BaseModel):
    phone: str
    email: str
    code: str

class AccessToken(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    
class RefreshToken(BaseModel):
    access_token: str

class ClientAppCreate(BaseModel):
    name: str
    description: str
    user: ModelBase
    
class ClientAppUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    user: Optional[ModelBase] = None
    
class ClientAppInDB(ModelInDBBase):
    name: str
    description: str
    client_id: str
    client_secret: str
    user: ModelInDBBase

class BandCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    band_type: str
    band_frequency: str
    lower: float
    upper: float
    rate: float

class BandUpdate(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    band_type: Optional[str] = None
    band_frequency: Optional[str] = None
    lower: Optional[float] = None
    upper: Optional[float] = None
    rate: Optional[float] = None

class BandInDB(ModelInDBBase):
    period_start: datetime
    period_end: datetime
    band_type: str
    band_frequency: str
    lower: Decimal
    upper: Decimal
    rate: Decimal

class CompanyCreate(BaseModel):
    name: str
    legal_name: Optional[str] = None
    description: Optional[str] = None
    pin_number: str
    nssf_number: Optional[str] = None
    shif_number: Optional[str] = None
    nita_number: Optional[str] = None
    contact_email: str
    contact_phone: Optional[str] = None
    address: Optional[str] = None

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    description: Optional[str] = None
    pin_number: Optional[str] = None
    nssf_number: Optional[str] = None
    shif_number: Optional[str] = None
    nita_number: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None

class CompanyInDB(ModelInDBBase):
    name: str
    legal_name: str
    description: str
    pin_number: str
    nssf_number: str
    shif_number: str
    nita_number: str
    contact_email: str
    contact_phone: str
    address: str

class StaffCreate(BaseModel):
    user: ModelInDBBase
    company: ModelInDBBase
    first_name: str
    last_name: str
    job_title: str
    department: Optional[str] = None
    contact_email: str
    contact_phone: Optional[str] = None
    pin_number: str
    staff_number: str
    shif_number: Optional[str] = None
    nssf_number: Optional[str] = None
    nita_number: Optional[str] = None
    national_id_number: str
    date_of_birth: datetime
    is_active: bool
    joined_on: datetime
    departed_on: Optional[datetime] = None
    bank_account_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_swift_code: Optional[str] = None
    bank_branch: Optional[str] = None

class StaffUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    pin_number: Optional[str] = None
    staff_number: Optional[str] = None
    shif_number: Optional[str] = None
    nssf_number: Optional[str] = None
    nita_number: Optional[str] = None
    national_id_number: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    is_active: Optional[bool] = None
    joined_on: Optional[datetime] = None
    departed_on: Optional[datetime] = None
    bank_account_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_swift_code: Optional[str] = None
    bank_branch: Optional[str] = None

class StaffInDB(ModelInDBBase):
    user: ModelInDBBase
    company: ModelInDBBase
    first_name: str
    last_name: str
    job_title: str
    department: str
    contact_email: str
    contact_phone: str
    pin_number: str
    staff_number: str
    shif_number: str
    nssf_number: str
    nita_number: str
    national_id_number: str
    date_of_birth: datetime
    is_active: bool
    joined_on: datetime
    departed_on: Optional[datetime] = None
    bank_account_number: str
    bank_name: str
    bank_swift_code: str
    bank_branch: str

class PayrollCodeCreate(BaseModel):
    company: ModelBase
    name: str
    description: Optional[str] = None
    variable: str
    code_type: str
    tags: Optional[List[str]] = []
    value: Optional[float] = None
    formula: Optional[str] = None
    order: int
    effective_from: datetime

class PayrollCodeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variable: Optional[str] = None
    code_type: Optional[str] = None
    tags: Optional[List[str]] = []
    value: Optional[float] = None
    formula: Optional[str] = None
    order: Optional[int] = None
    effective_from: Optional[datetime] = None

class PayrollCodeInDB(ModelInDBBase):
    company: ModelInDBBase
    name: str
    description: str
    variable: str
    code_type: str
    tags: List[str]
    value: float
    formula: str
    order: int
    effective_from: datetime

class ComputationCreate(BaseModel):
    company: ModelBase
    payroll_period_start: datetime
    payroll_period_end: datetime
    notes: Optional[str] = None
    status: str
    generated_by: ModelBase

class ComputationUpdate(BaseModel):
    payroll_period_start: Optional[datetime] = None
    payroll_period_end: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    generated_by: Optional[ModelBase] = None

class ComputationInDB(ModelInDBBase):
    company: ModelInDBBase
    payroll_period_start: datetime
    payroll_period_end: datetime
    notes: str
    status: str
    generated_by: ModelInDBBase

class ComputationComponentInDB(ModelInDBBase):
    computation: ModelBase
    payroll_code: ModelBase
    staff: ModelBase
    value: float
