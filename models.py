from email.policy import default
from enum import unique
import shutil
from fastapi import HTTPException
from mongoengine import *
from datetime import datetime, timezone, timedelta
from typing import Optional, Any, List, Dict, Tuple
from decimal import Decimal
from bson import ObjectId
import utils
from passlib.context import CryptContext
from config import logger
import jwt

# predefined formulae  
def calculate_paye(taxable_income: float, paye_bands_monthly: List[Dict[str, Decimal]]) -> Decimal:
    """
        Calculate PAYE based on the taxable income and the PAYE bands
    """
    paye: Decimal = 0.00
    for band in paye_bands_monthly:
        if taxable_income > band["upper"]:
            paye += (band["upper"] - band["lower"]) * (band["rate"] / 100)
        else:
            paye += (taxable_income - band["lower"]) * (band["rate"] / 100)
            break
    return paye

def calculate_nssf_contribution(gross_pay: float, nssf_bands_monthly: List[Dict[str, Decimal]]) -> Decimal:
    """
        Calculate NSSF contribution based on the gross pay and the NSSF bands
    """
    nssf_contribution: Decimal = 0.00
    for band in nssf_bands_monthly:
        if gross_pay > band["upper"]:
            nssf_contribution += (band["upper"] - band["lower"]) * band["rate"] / 100
        else:
            nssf_contribution += (gross_pay - band["lower"]) * band["rate"] / 100
            break
    return nssf_contribution

class BaseDocument(Document):
    meta = {'abstract': True}
    
    def to_dict(self):
        data = {}
        for field_name in self._fields:
            if field_name == 'id' or field_name == '_id':
                data['id'] = str(self.id)
                continue
                
            field_value = getattr(self, field_name)
            field = self._fields[field_name]
            if field_value is None:
                data[field_name] = None
                continue
            if isinstance(field, ReferenceField):
                if hasattr(field_value, 'to_pydantic_dict'):
                    data[field_name] = field_value.to_pydantic_dict()
                else:
                    ref_dict = field_value.to_mongo().to_dict()
                    if '_id' in ref_dict:
                        ref_dict['id'] = str(ref_dict.pop('_id'))
                    data[field_name] = ref_dict
            
            # Handle ListField with ReferenceField
            elif isinstance(field, ListField) and isinstance(field.field, ReferenceField):
                data[field_name] = []
                for item in field_value:
                    data[field_name].append(item.to_dict())        
            # Handle regular ListField
            elif isinstance(field, ListField):
                data[field_name] = [
                    item.to_pydantic_dict() if hasattr(item, 'to_pydantic_dict') 
                    else str(item) if isinstance(item, ObjectId)
                    else item 
                    for item in field_value
                ]
            
            # Handle EmbeddedDocumentField
            elif isinstance(field, EmbeddedDocumentField):
                if hasattr(field_value, 'to_pydantic_dict'):
                    data[field_name] = field_value.to_pydantic_dict()
                else:
                    data[field_name] = field_value.to_mongo().to_dict()
            
            # Handle ObjectId
            elif isinstance(field_value, ObjectId):
                data[field_name] = str(field_value)
            
            # Regular fields
            else:
                data[field_name] = field_value
                                
        return data

class ContentType(BaseDocument):
    """
    ContentType model representing different types of content in the system
    """
    model: str = StringField(required=True)
    object_id: Optional[ObjectId] = ObjectIdField(required=False)
    type_of_content: str = StringField(required=True, choices=['all_objects', 'specific_object'])
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()
    
    meta: Dict[str, Any] = {
        'collection': 'content_types',
        'indexes': [
            {'fields': ['model']}
        ]
    }

    def __str__(self) -> str:
        return f"ContentType: {self.model}"
    
    def __repr__(self) -> str:
        return f"<ContentType(id={self.id}, model={self.model})>"
    
    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        return super(ContentType, self).save(*args, **kwargs)

class Permission(BaseDocument):
    """
    Permission model that defines access controls
    Has a one-to-many relationship with ContentType
    """
    content_type: ContentType = ReferenceField(ContentType, required=True)
    codename: str = StringField(required=True)
    name: str = StringField(required=True)
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()
    
    meta: Dict[str, Any] = {
        'collection': 'permissions',
        'indexes': [
            {'fields': ['content_type', 'codename'], 'unique': True}
        ]
    }

    def __str__(self) -> str:
        return f"{self.name}"
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name}, codename={self.codename})>"
    
    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        return super(Permission, self).save(*args, **kwargs)

class Role(BaseDocument):
    """
    Role model that groups permissions
    Has a many-to-many relationship with Permission
    """
    name: str = StringField(required=True)
    description: str = StringField()
    permissions: List[Permission] = ListField(ReferenceField(Permission))
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()
    
    meta: Dict[str, Any] = {
        'collection': 'roles'
    }

    def __str__(self) -> str:
        return f"Role: {self.name}"
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name}, permissions_count={len(self.permissions)})>"
    
    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        return super(Role, self).save(*args, **kwargs)

class User(BaseDocument):
    """
    User model
    Has a many-to-many relationship with Role
    """
    name: str = StringField(required=True)
    email: str = EmailField(required=True, unique=True)
    is_email_verified: bool = BooleanField(default=False)
    email_verification_code: Optional[str] = StringField(max_length=50, required=False)
    email_verification_code_expiry: Optional[datetime] = DateTimeField(required=False)
    phone: str = StringField(max_length=50, unique=True)  # Using mediumtext equivalent
    is_phone_verified: bool = BooleanField(default=False)
    phone_verification_code: Optional[str] = StringField(max_length=50, required=False)
    phone_verification_code_expiry: Optional[datetime] = DateTimeField(required=False)
    password: str = StringField(required=True)
    is_active: bool = BooleanField(default=True)
    last_seen: Optional[datetime] = DateTimeField(required=False)  # Optional (datetime?)
    is_verified: bool = BooleanField(default=False)
    roles: List[Role] = ListField(ReferenceField(Role))
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()
    client_apps = ListField(ReferenceField('ClientApp'))

    meta: Dict[str, Any] = {
        'collection': 'users',
        'indexes': [
            {'fields': ['phone'], 'sparse': True}
        ]
    }

    def __str__(self) -> str:
        return f"{self.name}"
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, is_active={self.is_active}>"
    
    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        return super(User, self).save(*args, **kwargs)
    
    async def create_verification_code(self,code_length:int,code_expiry_seconds:int, mode: str = "phone") -> "User":
        """
            Create the verification code for the user and set it's expiry date and time
        """
        assert mode in ["phone","email"], "Invalid verification mode"
        if mode == "email":
            self.email_verification_code = utils.generate_random_string(length=code_length)
            self.email_verification_code_expiry = datetime.now() + timedelta(seconds=code_expiry_seconds)
        else:
            self.phone_verification_code = utils.generate_random_string(length=code_length)
            self.phone_verification_code_expiry = datetime.now() + timedelta(seconds=code_expiry_seconds)
        self.save()
        return self

    async def validate_verification_code(self,code:str, mode: str = "phone") -> bool:
        """
            Validate the verification code and activate the user
        """
        if mode == "email":
            if self.email_verification_code == code and self.email_verification_code_expiry > datetime.now():
                self.is_verified = True
                self.is_active = True
                self.email_verification_code = None
                self.email_verification_code_expiry = None
                logger.info(f"User {self.email} verified successfully")
                return True
            else:
                logger.info(f"User {self.email} verification failed")
                return False
        else:
            if self.phone_verification_code == code and self.phone_verification_code_expiry > datetime.now():
                self.is_verified = True
                self.is_active = True
                self.phone_verification_code = None
                self.phone_verification_code_expiry = None
                logger.info(f"User {self.phone} verified successfully")
                return True
            else:
                logger.info(f"User {self.phone} verification failed")
                return False
    
    async def has_perm(self,permission:str) -> bool:
        """
            Check if the user has the permission
        """
        for role in self.roles:
            for perm in role.permissions:
                if perm.codename == permission:
                    return True
        return False
    
    def set_password(self, password):
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.password = pwd_context.hash(password)
        self.save()

    def check_password(self, password):
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.password)
    
    def create_jwt_token(self, clientapp: "ClientApp", secret: str, algorithm: str, expiry_minutes: int) -> str:
        """
        Create a JWT token for the user, encoding the phone number and expiry time and return it
        """
        logger.info(f"Creating JWT token for user {self.phone}")
        expire = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        payload = {
            "sub": self.email,
            "exp": expire, 
            "client_id": clientapp.client_id,
            "client_secret": clientapp.client_secret
        }
        access_token = jwt.encode(payload=payload,key=secret,algorithm=algorithm)
        self.access_token = access_token
        return access_token
        
    
    @staticmethod
    def verify_jwt_token(token:str,secret:str,algorithm) -> Tuple[str,str,str] | None:
        """
            Verify the JWT token and return the phone number
        """
        logger.info(f"Verifying JWT token {token}")
        try:
            payload = jwt.decode(jwt=token,key=secret,algorithms=[algorithm],options={"verify_exp":True,"verify_signature":True,"required":["exp","sub"]})
            return payload.get("sub",None),payload.get("client_id",None),payload.get("client_secret",None)
        except jwt.InvalidAlgorithmError:
            logger.error(f"JWT token invalid algorithm: {algorithm} on token: {token}")
            raise HTTPException(status_code=401,detail={"message":"Invalid access token"})
        except jwt.ExpiredSignatureError:
            logger.error(f"JWT expired signature on token: {token}")
            raise HTTPException(status_code=401,detail={"message":"Access Token expired"})
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT invalid token: {token} error: {e}")
            raise HTTPException(status_code=401,detail={"message":"Invalid access token"})
    
    def has_permission(self, codename: str, content_type: Optional[Any] = None) -> bool:
        """Check if user has a specific permission"""            
        for role in self.roles:
            for permission in role.permissions:
                if permission.codename == codename:
                    if content_type is None or permission.content_type.id == content_type:
                        return True
        return False

class ClientApp(BaseDocument):
    """
    ClientApp model
    Has a many-to-one relationship with User
    """
    name: str = StringField()
    description: str = StringField()
    client_id: str = StringField(required=True, default = utils.generate_client_id)
    client_secret: str = StringField(required=True, default = utils.generate_client_secret)
    user: User = ReferenceField(User, reverse_delete_rule=CASCADE)
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()
    
    meta: Dict[str, Any] = {
        'collection': 'client_apps',
        'indexes': [
            {'fields': ['client_id'], 'unique': True}
            ]
    }
    
    def __str__(self) -> str:
        return f"{self.name} (Client App)"
    
    def __repr__(self) -> str:
        return f"<ClientApp(id={self.id}, name={self.name}, client_id={self.client_id})>"
    
    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        return super(ClientApp, self).save(*args, **kwargs)

# PAYE and NSSF bands
class Band(BaseDocument):
    """
    Represents a band for a payroll component.
    This document defines a band for a payroll component, including
    the lower and upper limits of the band, and the rate of the band.
    """
    period_start: datetime = DateTimeField(required=True, default=datetime.now(tz=timezone.utc))
    period_end: datetime = DateTimeField(required=True, default=datetime.now(tz=timezone.utc)+timedelta(days=365))
    band_type: str = StringField(required=True, choices=['PAYE', 'NSSF'])
    band_frequency: str = StringField(required=True, choices=['monthly', 'annual'], default='monthly')
    lower: float = DecimalField(required=True)
    upper: float = DecimalField(required=True, default=float("inf"))
    rate: float = DecimalField(required=True)
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()

    meta = {
        'collection': 'bands',
        'indexes': [
            ('lower', 'upper')
        ]
    }

    def __str__(self) -> str:
        return f"{self.lower} to {self.upper} at {self.rate}%"
    
    def __repr__(self) -> str:
        return f"Band(lower={self.lower}, upper={self.upper}, rate={self.rate})"

    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        return super(Band, self).save(*args, **kwargs)

class Company(BaseDocument):
    """
    Represents a company entity in the payroll system.
    This document stores core company information including legal details
    and contact information required for payroll processing.
    """
    name: str = StringField(required=True)
    legal_name: str = StringField(required=True)
    description: Optional[str] = StringField()
    pin_number: Optional[str] = StringField()
    nssf_number: Optional[str] = StringField()
    shif_number: Optional[str] = StringField()
    nita_number: Optional[str] = StringField()
    contact_email: Optional[str] = EmailField()
    contact_phone: Optional[str] = StringField()
    address: Optional[str] = StringField()
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()
    staff: List['Staff'] = ListField(ReferenceField('Staff'))

    meta = {
        'collection': 'companies'
    }

    def __str__(self) -> str:
        return f"{self.name} ({self.legal_name})"
    
    def __repr__(self) -> str:
        return f"Company(name='{self.name}', pin_number='{self.pin_number}')"
    
    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        return super(Company, self).save(*args, **kwargs)
    
    # clone master company's payroll codes to this company
    def clone_master_company(self):
        """
        Clone the master company's payroll codes to this company
        """
        master_company: 'Company' = Company.objects(name="Master Company").first()
        payroll_codes: List[PayrollCode] = PayrollCode.objects(company=master_company)
        for payroll_code in payroll_codes:
            new_payroll_code = PayrollCode(
                company=self,
                name=payroll_code.name,
                description=payroll_code.description,
                variable=payroll_code.variable,
                code_type=payroll_code.code_type,
                tags=payroll_code.tags,
                value=payroll_code.value,
                formula=payroll_code.formula,
                order=payroll_code.order,
                effective_from=datetime.now(tz=timezone.utc)
            )
            new_payroll_code.save()
        # clone the master company's template folder
        shutil.copytree(f"templates/{master_company.name}", f"templates/{self.name}", dirs_exist_ok=True)
        return True
    
    # roll forward the company's payroll codes
    def roll_forward(self, effective_from: datetime = datetime.now(tz=timezone.utc)):
        """
            Roll forward the company's payroll codes to a new effective date
        """
        payroll_codes: List[PayrollCode] = PayrollCode.objects(company=self, effective_from__lte=effective_from)
        for payroll_code in payroll_codes:
            new_payroll_code = PayrollCode(
                company=self,
                name=payroll_code.name,
                description=payroll_code.description,
                variable=payroll_code.variable,
                code_type=payroll_code.code_type,
                tags=payroll_code.tags,
                value=payroll_code.value,
                formula=payroll_code.formula,
                order=payroll_code.order,
                effective_from=effective_from
            )
            new_payroll_code.save()
        return True

class Staff(BaseDocument):
    """
    Represents an employee in the payroll system.
    This document stores employee personal information, identification numbers,
    and banking details required for payroll processing.
    """
    first_name: str = StringField(required=True)
    last_name: str = StringField(required=True)
    job_title: Optional[str] = StringField()
    department: Optional[str] = StringField()
    contact_email: str = EmailField(required=True)
    contact_phone: Optional[str] = StringField()
    pin_number: Optional[str] = StringField(required=True)
    staff_number: str = StringField(required=True)
    shif_number: Optional[str] = StringField()
    nssf_number: Optional[str] = StringField()
    nita_number: Optional[str] = StringField()
    national_id_number: Optional[str] = StringField()
    date_of_birth: Optional[datetime] = DateField()
    is_active: bool = BooleanField(default=True)
    joined_on: Optional[datetime] = DateTimeField(default=datetime.utcnow)
    departed_on: Optional[datetime] = DateTimeField()
    bank_account_number: Optional[str] = StringField(required=False)
    bank_name: Optional[str] = StringField(required=False)
    bank_swift_code: Optional[str] = StringField(required=False)
    bank_branch: Optional[str] = StringField(required=False)
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()
    company: 'Company' = ReferenceField('Company', required=True)
    user: Optional['User'] = ReferenceField('User')

    meta = {
        'collection': 'staff',
        'indexes': [
            'company',
            'national_id_number',
            ('first_name', 'last_name')
        ]
    }

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self) -> str:
        return f"Staff(name='{self.first_name} {self.last_name}', email='{self.contact_email}')"

    @property
    def full_name(self) -> str:
        """Returns the employee's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        return super(Staff, self).save(*args, **kwargs)

class PayrollCode(BaseDocument):
    """
    Represents a payroll component in the system.
    This document defines various components that make up an employee's pay,
    including both fixed and variable components, and their calculation rules.
    """
    company: 'Company' = ReferenceField('Company', required=True)
    name: str = StringField(required=True)
    description: Optional[str] = StringField()
    variable: str = StringField(required=False)
    code_type: str = StringField(required=True, choices=['input','fixed','formula'])
    tags: List[str] = ListField(StringField(), required=False)
    value: Optional[float] = DecimalField(default=-1)
    formula: Optional[str] = StringField(default="")
    order: int = IntField(default=0)
    effective_from: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()

    if code_type == "fixed":
        assert value not in [None, -1.0], "Fixed components must have a value"
    if code_type == "formula":
        assert formula not in [None,""], "Formula components must have a formula"
    if code_type == "input":
        assert value is None, "Input components must not have a value"
        assert formula is None, "Input components must not have a formula"

    meta = {
        'collection': 'payroll_components',
        'indexes': [
            'company',
            ('company', 'name'),
            ('company', 'effective_from')
        ]
    }

    def __str__(self) -> str:
        return f"{self.name} ({self.company.name})"
    
    def __repr__(self) -> str:
        return f"PayrollComponent(name='{self.name}', company='{self.company.name}')"
    
    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        # check if there is another component with the same order and company variable and effective from
        if PayrollCode.objects(company=self.company, order=self.order, effective_from=self.effective_from).count() > 0:
            raise ValidationError("Another Payroll Code with the same order and effective date exists")
        return super(PayrollCode, self).save(*args, **kwargs)

class Computation(BaseDocument):
    """
        Represents a payroll computation period.
        This document defines a specific payroll run for a company,
        including the period for which the payroll is being processed.
    """
    company: 'Company' = ReferenceField('Company', required=True)
    notes: Optional[str] = StringField()
    payroll_period_start: datetime = DateField(required=True)
    payroll_period_end: datetime = DateField(required=True)
    status: str = StringField(required=True, choices=['draft', 'processing', 'completed'], default='draft')
    generated_by: 'User' = ReferenceField('User', required=True)
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()

    meta = {
        'collection': 'computations',
        'indexes': [
            'company',
            ('company', 'payroll_period_start', 'payroll_period_end')
        ]
    }

    def __str__(self) -> str:
        return f"Computation ({self.company.name} - {self.payroll_period_start} to {self.payroll_period_end})"
    
    def __repr__(self) -> str:
        return f"Computation({self.company.name} - {self.payroll_period_start} to {self.payroll_period_end})"
    
    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        return super(Computation, self).save(*args, **kwargs)

    @property
    def period_display(self) -> str:
        """Returns a formatted string of the payroll period."""
        return f"{self.payroll_period_start.strftime('%Y-%m-%d')} to {self.payroll_period_end.strftime('%Y-%m-%d')}"
    
    def run(self):
        """
        Run the payroll computation for all staff members in the company
        Get all staff members in the company
        Get each staff member's computation components in order ascending
        Calculate the value of each component passing the dict of the previous components
        Save the value of the computed component
        """
        self.status = 'processing'
        self.save()
        staff: List[Staff] = Staff.objects(company=self.company)
        for employee in staff:
            params: Dict[str, float] = {}
            nssf_bands_monthly: List[Dict[str, Decimal]] = Band.objects(band_type='NSSF', band_frequency='monthly', period_start__lte=self.payroll_period_start, period_end__gte=self.payroll_period_start).order_by('lower')
            paye_bands_monthly: List[Dict[str, Decimal]] = Band.objects(band_type='PAYE', band_frequency='monthly', period_start__lte=self.payroll_period_start, period_end__gte=self.payroll_period_start).order_by('lower')
            params['nssf_bands_monthly'] = [band.to_dict() for band in nssf_bands_monthly]
            params['paye_bands_monthly'] = [band.to_dict() for band in paye_bands_monthly]
            payroll_codes: List[PayrollCode] = PayrollCode.objects(company=self.company, effective_from__lte=self.payroll_period_start).order_by('order')
            for payroll_code in payroll_codes:
                computation_component = ComputationComponent.objects(computation=self, payroll_component=payroll_code, staff=employee).first()
                if computation_component is None:
                    computation_component = ComputationComponent(computation=self, payroll_component=payroll_code, staff=employee)
                params[payroll_code.variable] = float(computation_component.calculate(params))
                computation_component.save()
            yield employee, params
        self.status = 'completed'
        self.save()

    
class ComputationComponent(BaseDocument):
    """
    Represents the intersection between Computation, PayrollComponent, and Staff.
    This document stores the actual computed values for each payroll component
    for each staff member within a specific computation period.
    """
    computation: 'Computation' = ReferenceField('Computation', required=True)
    payroll_component: 'PayrollCode' = ReferenceField('PayrollCode', required=True)
    staff: 'Staff' = ReferenceField('Staff', required=True)
    value: float = DecimalField(required=True, default=-1)
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()

    meta = {
        'collection': 'computation_components',
        'indexes': [
            ('computation', 'payroll_component', 'staff'),
            'computation',
            'staff'
        ]
    }

    def __str__(self) -> str:
        return f"{self.payroll_component.name} for {self.staff.full_name}"
    
    def __repr__(self) -> str:
        return f"ComputationComponent(component='{self.payroll_component.name}', staff='{self.staff.full_name}' value={self.value})"
        
    def calculate(self, params: Dict[str, float] = {}):
        """
            Calculate the value of the payroll component
        """
        if self.payroll_component.code_type == "input":
            assert self.value > -1, "Invalid value for input payroll component"
        if self.payroll_component.code_type == "fixed":
            self.value: float = self.payroll_component.value
        if self.payroll_component.code_type == "formula":
            self.value: float = eval(self.payroll_component.formula, globals(), params)
        return self.value
    
    def save(self, *args: Any, **kwargs: Any) -> Any:
        self.updated_at = datetime.now(tz=timezone.utc)
        return super(ComputationComponent, self).save(*args, **kwargs)