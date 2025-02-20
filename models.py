from mongoengine import *
from datetime import datetime
from typing import Optional, Any, List, Dict

# PAYE bands
"""
For example:
Effective 1st July 2023

Monthly Pay Bands (Ksh.)            Annual Pay Bands (Ksh.)             Rate of Tax (%)

On the first kShs. 24,000           On the first KShs. 288,000          10
On the next KShs. 8,333             On the next KShs.100,000            25
On the next KShs. 467,667           On the next KShs. 5,612,000         30
On the next KShs. 300,000           On the next KShs. 3,600,00          32.5
On all income above KShs. 800,000   On all income above KShs. 9,600,000 35

"""
paye_bands_monthly: List[Dict[float, float]] = [
   {
        "lower": 0.00,
        "upper": 24_000.00,
        "rate": 10.00
    },
    {
        "lower": 24_000.00,
        "upper": 32_333.00,
        "rate": 25.00
    },
    {
        "lower": 32_333.00,
        "upper": 500_000.00,
        "rate": 30.00
    },
    {
        "lower": 500_000.00,
        "upper": 800_000.00,
        "rate": 32.50
    },
    {
        "lower": 800_000.00,
        "upper": float("inf"),
        "rate": 35.00
    }
]

# NSSF bands
nssf_bands: List[Dict[float, float]] = [
    {
        "lower": 0.00,
        "upper": 7_000.00,
        "rate": 6.00
    },
    {
        "lower": 7_000.00,
        "upper": 36_000.00,
        "rate": 6.00
    }
]

# predefined formulae  
def calculate_paye(taxable_income: float) -> float:
    """
        Calculate PAYE based on the taxable income and the PAYE bands
    """
    paye: float = 0.00
    for band in paye_bands_monthly:
        if taxable_income > band["upper"]:
            paye += (band["upper"] - band["lower"]) * (band["rate"] / 100)
        else:
            paye += (taxable_income - band["lower"]) * (band["rate"] / 100)
            break
    return paye

def calculate_nssf_contribution(gross_pay: float) -> float:
    """
        Calculate NSSF contribution based on the gross pay and the NSSF bands
    """
    nssf_contribution: float = 0.00
    for band in nssf_bands:
        if gross_pay > band["upper"]:
            nssf_contribution += (band["upper"] - band["lower"]) * band["rate"] / 100
        else:
            nssf_contribution += (gross_pay - band["lower"]) * band["rate"] / 100
            break
    return nssf_contribution

class Company(Document):
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

    meta = {
        'collection': 'companies'
    }

    def __str__(self) -> str:
        return f"{self.name} ({self.legal_name})"
    
    def __repr__(self) -> str:
        return f"Company(name='{self.name}', pin_number='{self.pin_number}')"

class Staff(Document):
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
    company: 'Company' = ReferenceField('Company', required=True)

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

class PayrollComponent(Document):
    """
    Represents a payroll component in the system.
    
    This document defines various components that make up an employee's pay,
    including both fixed and variable components, and their calculation rules.
    """
    company: 'Company' = ReferenceField('Company', required=True)
    name: str = StringField(required=True)
    description: Optional[str] = StringField()
    variable: str = StringField(required=False)
    component_type: str = StringField(required=True, choices=['input','fixed','formula'])
    value: Optional[float] = DecimalField()
    formula: Optional[str] = StringField()
    order: int = IntField(default=0)
    effective_from: datetime = DateTimeField(default=datetime.utcnow)
    if component_type == "fixed":
        assert value is not None, "Fixed components must have a value"
    if component_type == "formula":
        assert formula is not None, "Formula components must have a formula"
    if component_type == "input":
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

class Computation(Document):
    """
    Represents a payroll computation period.
    
    This document defines a specific payroll run for a company,
    including the period for which the payroll is being processed.
    """
    company: 'Company' = ReferenceField('Company', required=True)
    notes: Optional[str] = StringField()
    payroll_period_start: datetime = DateField(required=True)
    payroll_period_end: datetime = DateField(required=True)

    meta = {
        'collection': 'computations',
        'indexes': [
            'company',
            ('company', 'payroll_period_start', 'payroll_period_end')
        ]
    }

    def __str__(self) -> str:
        return f"{self.name} ({self.payroll_period_start} to {self.payroll_period_end})"
    
    def __repr__(self) -> str:
        return f"Computation(name='{self.name}', company='{self.company.name}')"

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
            payroll_components: List[PayrollComponent] = PayrollComponent.objects(company=self.company).order_by('order')
            for payroll_component in payroll_components:
                computation_component = ComputationComponent.objects(computation=self, payroll_component=payroll_component, staff=employee).first()
                if computation_component is None:
                    computation_component = ComputationComponent(computation=self, payroll_component=payroll_component, staff=employee)
                params[payroll_component.variable] = float(computation_component.calculate(params))
                computation_component.save()
            yield employee, params

class ComputationComponent(Document):
    """
    Represents the intersection between Computation, PayrollComponent, and Staff.
    
    This document stores the actual computed values for each payroll component
    for each staff member within a specific computation period.
    """
    computation: 'Computation' = ReferenceField('Computation', required=True)
    payroll_component: 'PayrollComponent' = ReferenceField('PayrollComponent', required=True)
    staff: 'Staff' = ReferenceField('Staff', required=True)
    value: float = DecimalField(required=True)

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
        if self.payroll_component.component_type == "input":
            assert self.value > -1, "Invalid value for input payroll component"
        if self.payroll_component.component_type == "fixed":
            self.value: float = self.payroll_component.value
        if self.payroll_component.component_type == "formula":
            self.value: float = eval(self.payroll_component.formula, globals(), params)
        return self.value