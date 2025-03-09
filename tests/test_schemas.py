import schemas
import models
import utils

from faker import Faker

fake = Faker()

def test_common_schemas(db):
    # test list response schema
    content_types = models.ContentType.objects.all()
    list_response = schemas.ListResponse(**{
        "total": len(content_types),
        "page": 1,
        "size": len(content_types),
        "data": [schemas.ContentTypeInDB.model_validate(content_type.to_dict()).model_dump() for content_type in content_types]
    })
    list_response_dict = list_response.model_dump()
    assert list_response_dict["total"] == len(content_types)
    assert list_response_dict["page"] == 1
    assert list_response_dict["size"]  == len(content_types)
    assert len(list_response_dict["data"]) == len(content_types)

    # test model base schema
    content_type = models.ContentType.objects.first()
    content_type_dict = schemas.ModelBase.model_validate(content_type.to_dict()).model_dump()
    assert content_type_dict["id"] == str(content_type.id)

    # test model in db base schema
    content_type = models.ContentType.objects.first()
    content_type.id = str(content_type.id)
    content_type_dict = schemas.ModelInDBBase.model_validate(content_type).model_dump()
    assert content_type_dict["id"] == str(content_type.id)
    assert content_type_dict["created_at"] is not None
    assert content_type_dict["updated_at"] is not None

def test_auth_schemas(db):
    # test content type schema
    content_type = models.ContentType.objects.first()
    content_type_dict = schemas.ContentTypeInDB.model_validate(content_type.to_dict()).model_dump()
    assert content_type_dict["id"] == str(content_type.id)
    assert content_type_dict["model"] == content_type.model
    assert content_type_dict["object_id"] == (str(content_type.object_id) if content_type.object_id else None)
    assert content_type_dict["type_of_content"] == content_type.type_of_content

    # test permission create schema
    content_type = models.ContentType.objects.first()
    permission_create = schemas.PermissionCreate(**{
        "content_type": schemas.ModelInDBBase.model_validate(content_type.to_dict()).model_dump(),
        "codename": utils.generate_random_string(6),
        "name": utils.generate_random_string(6)
    })
    permission_create_dict = permission_create.model_dump()
    assert permission_create_dict["content_type"]["id"] == str(content_type.id)
    assert permission_create_dict["codename"] == permission_create.codename
    assert permission_create_dict["name"] == permission_create.name

    # test permission update schema
    content_type = models.ContentType.objects.first()
    permission = models.Permission.objects.first()
    permission_update = schemas.PermissionUpdate(**{
        "name": fake.word(),
        "codename": fake.word(),
        "content_type": permission.content_type.to_dict()
    })
    permission_update_dict = permission_update.model_dump()
    assert permission_update_dict["name"] == permission_update.name
    assert permission_update_dict["codename"] == permission_update.codename
    assert permission_update_dict["content_type"]["id"] == str(permission.content_type.id)

    # test permission in db schema
    permission = models.Permission.objects.first()
    permission_dict = schemas.PermissionInDB.model_validate(permission.to_dict()).model_dump()
    assert permission_dict["id"] == str(permission.id)
    assert permission_dict["name"] == permission.name
    assert permission_dict["codename"] == permission.codename
    assert permission_dict["content_type"]["id"] == str(permission.content_type.id)

    # test role create schema
    role_create = schemas.RoleCreate(**{
        "name": fake.word(),
        "description": fake.word(),
        "permissions": [schemas.ModelInDBBase.model_validate(permission.to_dict()).model_dump() for permission in models.Permission.objects.all()]
    })
    assert role_create.name is not None
    assert role_create.description is not None
    assert len(role_create.permissions) == len(models.Permission.objects.all())

    # test role update schema
    role = models.Role.objects.first()
    role_update = schemas.RoleUpdate(**{
        "name": fake.word(),
        "description": fake.word(),
        "permissions": [permission.to_dict() for permission in models.Permission.objects.all()]
    })
    assert role_update.name is not None
    assert role_update.description is not None
    assert len(role_update.permissions) == len(models.Permission.objects.all())
    
    # test role in db schema
    role = models.Role.objects.first()
    role_dict = schemas.RoleInDB.model_validate(role.to_dict()).model_dump()
    assert role_dict["id"] == str(role.id)
    assert role_dict["name"] == role.name
    assert len(role_dict["permissions"]) == len(role.permissions)

    # test user create schema
    user_create = schemas.UserCreate(**{
        "name": fake.name(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "password": fake.password()
    })
    assert user_create.name is not None
    assert user_create.email is not None
    assert user_create.phone is not None
    assert user_create.password is not None

    # test user update schema
    user = models.User.objects.first()
    user_update = schemas.UserUpdate(**{
        "name": fake.name(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "password": fake.password()
    })
    assert user_update.name is not None
    assert user_update.email is not None
    assert user_update.phone is not None
    assert user_update.password is not None

    # test user in db schema
    user = models.User.objects.first()
    user_dict = schemas.UserInDB.model_validate(user.to_dict()).model_dump()
    assert user_dict["id"] == str(user.id)
    assert user_dict["name"] == user.name
    assert user_dict["email"] == user.email
    assert user_dict["phone"] == user.phone
    assert len(user_dict["roles"]) == len(user.roles)

    # test user verify schema
    user = models.User.objects.first()
    user_verify = schemas.UserVerify(**{
        "code": utils.generate_random_string(6),
        "email": user.email,
        "phone": user.phone
    })
    assert user_verify.code is not None
    assert user_verify.email is not None
    assert user_verify.phone is not None

    # test access and refresh token schema
    access_token = schemas.AccessToken(**{
        "access_token": utils.generate_random_string(6),
        "expires_in": 3600
    })
    assert access_token.access_token is not None
    assert access_token.expires_in is not None

    refresh_token = schemas.RefreshToken(**{
        "access_token": utils.generate_random_string(6)
    })
    assert refresh_token.access_token is not None

    # test client app create, update schemas and client app in db schema
    user = models.User.objects.first()
    client_app_create = schemas.ClientAppCreate(**{
        "name": fake.company(),
        "description": fake.sentence(),
        "user": schemas.ModelInDBBase.model_validate(user.to_dict()).model_dump()
    })
    assert client_app_create.name is not None
    assert client_app_create.description is not None
    assert client_app_create.user is not None

    client_app = models.ClientApp.objects.first()
    client_app_update = schemas.ClientAppUpdate(**{
        "name": fake.company(),
        "description": fake.sentence(),
        "user": user.to_dict()
    })
    assert client_app_update.name is not None
    assert client_app_update.description is not None
    assert client_app_update.user is not None

    client_app_dict = schemas.ClientAppInDB.model_validate(client_app.to_dict()).model_dump()
    assert client_app_dict["id"] == str(client_app.id)

def test_payroll_schemas(db):
    # test band schema
    band_create = schemas.BandCreate(**{
        "period_start": fake.date_time_this_year(),
        "period_end": fake.date_time_this_year(),
        "band_type": "PAYE",
        "band_frequency": "monthly",
        "lower": 0,
        "upper": 24000,
        "rate": 0.1
    })
    assert band_create.period_start is not None
    assert band_create.period_end is not None
    assert band_create.band_type is not None
    assert band_create.band_frequency is not None
    assert band_create.lower is not None
    assert band_create.upper is not None
    assert band_create.rate is not None

    band_update = schemas.BandUpdate(**{
        "period_start": fake.date_time_this_year(),
        "period_end": fake.date_time_this_year(),
        "band_type": "PAYE",
        "band_frequency": "monthly",
        "lower": 0,
        "upper": 24000,
        "rate": 0.1
    })
    assert band_update.period_start is not None
    assert band_update.period_end is not None
    assert band_update.band_type is not None
    assert band_update.band_frequency is not None
    assert band_update.lower is not None
    assert band_update.upper is not None
    assert band_update.rate is not None

    band = models.Band.objects.first()
    band_dict = schemas.BandInDB.model_validate(band.to_dict()).model_dump()
    assert band_dict["id"] == str(band.id)
    assert band_dict["period_start"] == band.period_start
    assert band_dict["period_end"] == band.period_end
    assert band_dict["band_type"] == band.band_type
    assert band_dict["band_frequency"] == band.band_frequency
    assert band_dict["lower"] == band.lower
    assert band_dict["upper"] == band.upper
    assert band_dict["rate"] == band.rate

    # test company schema
    company_create = schemas.CompanyCreate(**{
        "name": fake.company(),
        "legal_name": fake.company() + " Ltd.",
        "description": fake.text(),
        "pin_number": "auth",
        "nssf_number": "auth",
        "shif_number": "auth",
        "nita_number": "auth",
        "contact_email": fake.company_email(),
        "contact_phone": fake.phone_number(),
        "address": fake.address()
    })
    assert company_create.name is not None
    assert company_create.legal_name is not None

    company_update = schemas.CompanyUpdate(**{
        "name": fake.company(),
        "legal_name": fake.company() + " Ltd.",
        "description": fake.text(),
        "pin_number": "auth",
        "nssf_number": "auth",
        "shif_number": "auth",
        "nita_number": "auth",
        "contact_email": fake.company_email(),
        "contact_phone": fake.phone_number(),
        "address": fake.address()
    })
    assert company_update.name is not None
    assert company_update.legal_name is not None

    company = models.Company.objects.first()
    company_dict = schemas.CompanyInDB.model_validate(company.to_dict()).model_dump()
    assert company_dict["id"] == str(company.id)

    # test staff schema
    company = models.Company.objects.first()
    user = models.User.objects.first()
    staff_create = schemas.StaffCreate(**{
        "user": {"id": str(user.id)},
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "job_title": fake.job(),
        "department": fake.word(),
        "contact_email": fake.email(),
        "contact_phone": fake.phone_number(),
        "pin_number": "auth",
        "staff_number": "auth",
        "shif_number": "auth",
        "nssf_number": "auth",
        "nita_number": "auth",
        "national_id_number": "auth",
        "date_of_birth": fake.date_of_birth(),
        "is_active": True,
        "joined_on": fake.date_time()
    })
    assert staff_create.user is not None
    assert staff_create.first_name is not None

    # test staff update schema
    staff = models.Staff.objects.first()
    staff_update = schemas.StaffUpdate(**{
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "job_title": fake.job(),
        "department": fake.word(),
        "contact_email": fake.email(),
        "contact_phone": fake.phone_number(),
        "pin_number": "auth",
        "staff_number": "auth",
        "shif_number": "auth",
        "nssf_number": "auth",
        "nita_number": "auth",
        "national_id_number": "auth"
    })
    assert staff_update.first_name is not None
    assert staff_update.last_name is not None
    assert staff_update.job_title is not None
    assert staff_update.department is not None

    staff = models.Staff.objects.first()
    staff_dict = schemas.StaffInDB.model_validate(staff.to_dict()).model_dump()
    assert staff_dict["id"] == str(staff.id)
    assert staff_dict["first_name"] == staff.first_name
    assert staff_dict["last_name"] == staff.last_name
    assert staff_dict["job_title"] == staff.job_title
    assert staff_dict["department"] == staff.department

    # test payroll code schema
    company = models.Company.objects.first()
    payroll_code_create = schemas.PayrollCodeCreate(**{
        "name": "BASE",
        "description": "Base Salary",
        "variable": "base_salary",
        "code_type": "input",
        "value": 1000,
        "tags": ["COMPENSATION"],
        "formula":"",
        "order": 1,
        "effective_from": fake.date_time_this_year()
    })
    assert payroll_code_create.name is not None

    payroll_code_update = schemas.PayrollCodeUpdate(**{
        "name": "BASE",
        "description": "Base Salary",
        "variable": "base_salary",
        "code_type": "input",
        "value": 1000,
        "tags": ["COMPENSATION"],
        "formula":"",
        "order": 1,
        "effective_from": fake.date_time_this_year()
    })
    assert payroll_code_update.name is not None
    assert payroll_code_update.variable is not None
    assert payroll_code_update.code_type is not None

    payroll_code = models.PayrollCode.objects.first()
    payroll_code_dict = schemas.PayrollCodeInDB.model_validate(payroll_code.to_dict()).model_dump()
    assert payroll_code_dict["id"] == str(payroll_code.id)
    assert payroll_code_dict["name"] == payroll_code.name

    # test computation schema
    company = models.Company.objects.first()
    payroll_computation_create = schemas.ComputationCreate(**{
        "notes": fake.text(),
        "payroll_period_start": fake.date_time_this_year(),
        "payroll_period_end": fake.date_time_this_year(),
        "status": "draft",
        "generated_by": {"id": str(models.User.objects.first().id)}
    })
    assert payroll_computation_create.notes is not None
    assert payroll_computation_create.payroll_period_start is not None
    assert payroll_computation_create.payroll_period_end is not None

    payroll_computation_update = schemas.ComputationUpdate(**{
        "notes": fake.text(),
        "payroll_period_start": fake.date_time_this_year(),
        "payroll_period_end": fake.date_time_this_year(),
        "status": "processing",
        "generated_by": user.to_dict()
    })
    assert payroll_computation_update.notes is not None
    assert payroll_computation_update.payroll_period_start is not None
    assert payroll_computation_update.payroll_period_end is not None
    assert payroll_computation_update.status == "processing"

    computation = models.Computation.objects.first()
    computation_dict = schemas.ComputationInDB.model_validate(computation.to_dict()).model_dump()
    assert computation_dict["id"] == str(computation.id)
    assert computation_dict["notes"] == computation.notes
    assert computation_dict["status"] == computation.status

    # test computation component schema
    computation_component = models.ComputationComponent.objects.first()
    computation_component_dict = schemas.ComputationComponentInDB.model_validate(computation_component.to_dict()).model_dump()
    assert computation_component_dict["id"] == str(computation_component.id)
    assert computation_component_dict["value"] == computation_component.value
    
