import base64
import datetime
import json
from mimetypes import init
import uuid
import secrets
import string
import nanoid
from pydantic_settings import BaseSettings
import models
import config
from config import settings
import requests
from typing import Tuple

def initialize_master_company():
    master_company = models.Company.objects.filter(name="Master Company").first()
    if not master_company:
        master_company = models.Company(
            name="Master Company",
            legal_name="Master Company International Ltd.",
            description="This is the master company that contains main configurations. These configurations are used as defaults for all other companies.",
            pin_number  = generate_random_string(10)+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            nssf_number = generate_random_string(10)+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            shif_number = generate_random_string(10)+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            nita_number = generate_random_string(10)+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            contact_email = "master@hummingbird.com",
            contact_phone= "+254712345678",
            address="Master Company Address"
        )
        master_company.save()
    gross_pay: models.PayrollCode = models.PayrollCode(company=master_company, name="Gross Pay", description="Gross Pay", variable="gross_pay", code_type="input", order=0,  effective_from=datetime.datetime(2020, 1, 1))
    gross_pay.save()
    pension_benefit: models.PayrollCode = models.PayrollCode(company=master_company, name="Pension Benefit", description="Pension Benefit", variable="pension_benefit", code_type="input", order=1,  effective_from=datetime.datetime(2020, 1, 1))
    pension_benefit.save()
    personal_relief_monthly: models.PayrollCode = models.PayrollCode(company=master_company, name="Personal Relief Monthly", description="Personal Relief Monthly", variable="personal_relief_monthly", code_type="fixed", order=2,  value=2_400.00, effective_from=datetime.datetime(2020, 1, 1))
    personal_relief_monthly.save()
    nita: models.PayrollCode = models.PayrollCode(company=master_company, name="NITA", description="NITA", variable="nita", code_type="fixed", order=3,  value=50.00, effective_from=datetime.datetime(2020, 1, 1))
    nita.save()
    nssf_contribution_employee: models.PayrollCode = models.PayrollCode(company=master_company, name="NSSF Contribution", description="NSSF Contribution", variable="nssf_contribution_employee", code_type="formula", order=4, formula="calculate_nssf_contribution(gross_pay)",  effective_from=datetime.datetime(2020, 1, 1))
    nssf_contribution_employee.save()
    affordable_housing_levy: models.PayrollCode = models.PayrollCode(company=master_company, name="Affordable Housing Levy", description="Affordable Housing Levy", variable="affordable_housing_levy", code_type="formula", order=5, formula="0.015 * gross_pay",  effective_from=datetime.datetime(2020, 1, 1))
    affordable_housing_levy.save()
    affordable_housing_relief: models.PayrollCode = models.PayrollCode(company=master_company, name="Affordable Housing Relief", description="Affordable Housing Relief", variable="affordable_housing_relief", code_type="formula", order=6, formula="0.15 * affordable_housing_levy",  effective_from=datetime.datetime(2020, 1, 1))
    affordable_housing_relief.save()
    shif_contribution: models.PayrollCode = models.PayrollCode(company=master_company, name="SHIF Contribution", description="SHIF Contribution", variable="shif_contribution", code_type="formula", order=7, formula="0.0275 * gross_pay",  effective_from=datetime.datetime(2020, 1, 1))
    shif_contribution.save()
    deductable_shif_contribution: models.PayrollCode = models.PayrollCode(company=master_company, name="Deductable SHIF Contribution", description="Deductable SHIF Contribution", variable="deductable_shif_contribution", code_type="formula", order=8, formula="0.15 * shif_contribution",  effective_from=datetime.datetime(2020, 1, 1))
    deductable_shif_contribution.save()
    taxable_income: models.PayrollCode = models.PayrollCode(company=master_company, name="Taxable Income", description="Taxable Income", variable="taxable_income", code_type="formula", order=9, formula="gross_pay + pension_benefit - nssf_contribution_employee",  effective_from=datetime.datetime(2020, 1, 1))
    taxable_income.save()
    gross_paye: models.PayrollCode = models.PayrollCode(company=master_company, name="Gross PAYE", description="Gross PAYE", variable="gross_paye", code_type="formula", order=10, formula="calculate_paye(taxable_income)",  effective_from=datetime.datetime(2020, 1, 1))
    gross_paye.save()
    net_paye: models.PayrollCode = models.PayrollCode(company=master_company, name="Net PAYE", description="Net PAYE", variable="net_paye", code_type="formula", order=11, formula="gross_paye - personal_relief_monthly - affordable_housing_relief",  effective_from=datetime.datetime(2020, 1, 1))
    net_paye.save()
    affordable_housing_levy_employer: models.PayrollCode = models.PayrollCode(company=master_company, name="Affordable Housing Levy Employer", description="Affordable Housing Levy Employer", variable="affordable_housing_levy_employer", code_type="formula", order=12, formula="0.015 * gross_pay",  effective_from=datetime.datetime(2020, 1, 1))
    affordable_housing_levy_employer.save()
    nssf_contribution_employer: models.PayrollCode = models.PayrollCode(company=master_company, name="NSSF Contribution Employer", description="NSSF Contribution Employer", variable="nssf_contribution_employer", code_type="formula", order=13, formula="calculate_nssf_contribution(gross_pay)",  effective_from=datetime.datetime(2020, 1, 1))
    nssf_contribution_employer.save()
    total_deductions: models.PayrollCode = models.PayrollCode(company=master_company, name="Total Deductions", description="Total Deductions", variable="total_deductions", code_type="formula", order=14, formula="nssf_contribution_employee + net_paye + shif_contribution + affordable_housing_levy",  effective_from=datetime.datetime(2020, 1, 1))
    total_deductions.save()
    net_pay: models.PayrollCode = models.PayrollCode(company=master_company, name="Net Pay", description="Net Pay", variable="net_pay", code_type="formula", order=15, formula="gross_pay - total_deductions",  effective_from=datetime.datetime(2020, 1, 1))
    net_pay.save()
    return master_company

def mailtrap_send_email(to: Tuple[str,str], subject: str, message: str) -> bool:
    try:
        to_email, to_name = to
        url = "https://send.api.mailtrap.io/api/send"
        payload = {
            "to": [
                {
                    "email": to_email,
                    "name": to_name
                }
            ],
            "from": {
                "email": "hi@demomailtrap.com",
                "name": "Deployment Bot"
            },
            "subject": subject,
            "text": message,
            "category": "Hummingbird"
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Api-Token": settings.mailtrap_api_token
        }
        response = requests.post(url, json=payload, headers=headers)
    except Exception as e:
        raise e

def initialize_db(settings: BaseSettings, is_test: bool = False):
    for model in config.DEFAULT_CONTENT_CLASSES:
        content_types = models.ContentType.objects.filter(model=model).all()
        if not content_types:
            content_type = models.ContentType(model=model, type_of_content="all_objects")
            content_type.save()
        else:
            content_type = content_types[0]
        for permission in config.DEFAULT_PERMISSIONS_CLASSES:
            if not models.Permission.objects.filter(codename=permission+"_"+content_type.model).all():
                permission_db = models.Permission()
                permission_db.name = permission.title()+" "+content_type.model
                permission_db.codename = permission+"_"+content_type.model
                permission_db.content_type = content_type
                permission_db.save()
    # create superuser role
    superuser_role = models.Role.objects(name="Admin").all()
    if not superuser_role:
        superuser_role = models.Role(name="Admin",description="Superuser Role")
        for permission in models.Permission.objects.all():
            superuser_role.permissions.append(permission)
        superuser_role.save()
    else:
        superuser_role = superuser_role[0]
    # create payrolladmin role
    payrolladmin_role = models.Role.objects(name="PayrollAdmin").all()
    if not payrolladmin_role:
        payrolladmin_role = models.Role(name="PayrollAdmin",description="Payroll Admin Role")
        for permission in models.Permission.objects.all():
            payrolladmin_role.permissions.append(permission)
        payrolladmin_role.save()
    else:
        payrolladmin_role = payrolladmin_role[0]
    # create staff role
    staff_role = models.Role.objects(name="Staff").all()
    if not staff_role:
        staff_role = models.Role(name="Staff",description="Staff Role")
        for permission in models.Permission.objects.all():
            staff_role.permissions.append(permission)
        staff_role.save()
    else:
        staff_role = staff_role[0]
    # create superuser
    superuser = models.User.objects(phone=settings.superuser_phone).first()
    if not superuser:
        superuser = models.User(phone=settings.superuser_phone,email=settings.superuser_email,name="Admin", is_active=True, is_verified=True)
        superuser.roles.append(superuser_role)
        superuser.set_password(settings.superuser_password)
        superuser.save()
    # create default clientapp
    clientapp = models.ClientApp.objects(name="DefaultApp").first()
    if not clientapp:
        clientapp = models.ClientApp(name="DefaultApp",description="Default Application",user=superuser)
        clientapp.save()
    if not is_test:
        client_credentials_email = f"""
            Hello Admin,
            Your superuser phone number is: {superuser.phone}
            Your default clientapp credentials are:
            Client ID: {clientapp.client_id}
            Client Secret: {clientapp.client_secret}
        """
        mailtrap_send_email(to=("kahenya0@gmail.com","System Admin"),subject="Hummingbird Superuser Credentials",message=client_credentials_email)
    initialize_master_company()

def generate_random_string(length:int=6) -> str:
    choice_characters = string.ascii_uppercase+ string.digits
    random_string = ''.join(secrets.choice(choice_characters) for _ in range(length))
    return random_string

def generate_unique_socket_room_id() -> str:
    alphabet = string.ascii_lowercase+ string.digits
    return nanoid.generate(alphabet,50)

def generate_client_id() -> str:
    return str(uuid.uuid4())

def generate_client_secret() -> str:
    return secrets.token_urlsafe(50)


async def smsleopard_send_sms(phone: str, message: str) -> bool:
    try:
        phone = phone.strip()
        # mailtrap_send_email(("kahenya0@gmail.com","System Admin"),f"Backup OTP for {phone}",f"Your OTP is {message}")
        url = f"{settings.smsleopard_base_url}/sms/send"
        credentials = f"{settings.smsleopard_api_key}:{settings.smsleopard_api_secret}"
        headers = {
            "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}"
        }
        body = {
            "source": "smsleopard",
            "destination": [{"number": phone}],
            "message": message
        }
        response = requests.post(url, data=json.dumps(body), headers=headers)
        if response.status_code == 201 and response.json().get("success"):
            return True
        else:
            raise Exception(f"{response.status_code} - {response.text}")
    except Exception as e:
        raise e
    

if __name__ == '__main__':
    try:
        mailtrap_send_email(to=("kahenya0@gmail.com","System Admin"),subject="Hummingbird Superuser Credentials",message="Hello Admin, Your superuser phone number is: 0712345678")
    except Exception as e:
        print(f"Error initializing app: {e}")
        raise e