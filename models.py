from email.policy import default
from enum import unique
from mongoengine import *
from datetime import datetime, timezone, timedelta
from typing import Optional, Any, List, Dict
from decimal import Decimal
import uuid
from bson import ObjectId
import utils

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
    phone: str = StringField(max_length=50, unique=True)  # Using mediumtext equivalent
    password: str = StringField(required=True)
    is_active: bool = BooleanField(default=True)
    last_seen: Optional[datetime] = DateTimeField(required=False)  # Optional (datetime?)
    phone_verification_code: Optional[str] = StringField(max_length=50, required=False)  # Optional (mediumtext?)
    phone_verification_code_expiry: Optional[datetime] = DateTimeField(required=False)  # Optional (datetime?)
    is_verified: bool = BooleanField(default=False)
    roles: List[Role] = ListField(ReferenceField(Role))
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()
    
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
    client_id: str = StringField(required=True, default = utils.generate_client_id())
    client_secret: str = StringField(required=True, default = utils.generate_client_secret())
    user: User = ReferenceField(User)
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
    bank_account_number: Optional[str] = StringField()
    bank_name: Optional[str] = StringField()
    bank_swift_code: Optional[str] = StringField()
    bank_branch: Optional[str] = StringField()
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
    value: Optional[float] = DecimalField()
    formula: Optional[str] = StringField()
    order: int = IntField(default=0)
    effective_from: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    created_at: datetime = DateTimeField(default=datetime.now(tz=timezone.utc))
    updated_at: datetime = DateTimeField()

    if code_type == "fixed":
        assert value is not None, "Fixed components must have a value"
    if code_type == "formula":
        assert formula is not None, "Formula components must have a formula"
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
    status: str = StringField(required=True, choices=['draft', 'processing', 'completed', 'cancelled'], default='draft')
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
        staff: List[Staff] = Staff.objects(company=self.company)
        for employee in staff:
            params: Dict[str, float] = {}
            nssf_bands_monthly: List[Dict[str, Decimal]] = Band.objects(band_type='NSSF', band_frequency='monthly', period_start__lte=self.payroll_period_start, period_end__gte=self.payroll_period_start).order_by('lower')
            paye_bands_monthly: List[Dict[str, Decimal]] = Band.objects(band_type='PAYE', band_frequency='monthly', period_start__lte=self.payroll_period_start, period_end__gte=self.payroll_period_start).order_by('lower')
            params['nssf_bands_monthly'] = [band.to_dict() for band in nssf_bands_monthly]
            params['paye_bands_monthly'] = [band.to_dict() for band in paye_bands_monthly]
            payroll_components: List[PayrollCode] = PayrollCode.objects(company=self.company, effective_from__gte=self.payroll_period_start).order_by('order')
            for payroll_component in payroll_components:
                computation_component = ComputationComponent.objects(computation=self, payroll_component=payroll_component, staff=employee).first()
                if computation_component is None:
                    computation_component = ComputationComponent(computation=self, payroll_component=payroll_component, staff=employee)
                params[payroll_component.variable] = float(computation_component.calculate(params))
                computation_component.save()
            yield employee, params

class ComputationComponent(BaseDocument):
    """
    Represents the intersection between Computation, PayrollComponent, and Staff.
    This document stores the actual computed values for each payroll component
    for each staff member within a specific computation period.
    """
    computation: 'Computation' = ReferenceField('Computation', required=True)
    payroll_component: 'PayrollCode' = ReferenceField('PayrollCode', required=True)
    staff: 'Staff' = ReferenceField('Staff', required=True)
    value: float = DecimalField(required=True)
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
        return f"ComputationComponent(component='{self.payroll_component.name}', staff='{self.staff.full_name}')"
        
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