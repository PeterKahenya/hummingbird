import datetime
import json
from unittest.mock import patch
import pytest
import models
from .conftest import settings as test_settings
import faker
import pandas as pd
import os
import io

pytest_plugins = ('pytest_asyncio',)
fake = faker.Faker()
    
"""Test API"""

# test authentication api calls
async def authenticate(client, db):
    app = models.ClientApp.objects.first()
    user = models.User.objects.filter(phone=test_settings.superuser_phone).first()
    # test login by sending phone, client_id, client_secret as form data
    response = client.post("/auth/login",data={ "email": user.email, "password": test_settings.superuser_password, "client_id": app.client_id, "client_secret": app.client_secret})
    assert response.status_code == 200
    assert response.json()["access_token"] != None
    access_token = response.json()["access_token"]
    # test phone verification
    response = client.post("/auth/verify-phone/request",data = {"phone": user.phone, "client_id": app.client_id,"client_secret": app.client_secret})
    assert response.status_code == 200
    assert response.json()["message"] == "SMS verification code sent"
    user.reload()
    response = client.post("/auth/verify-phone/verify", data = {"phone": user.phone, "code": user.phone_verification_code, "client_id": app.client_id,"client_secret": app.client_secret})
    assert response.status_code == 200
    assert response.json()["message"] == "Phone verified"
    # test email verification
    response = client.post("/auth/verify-email/request",data={"email": user.email, "client_id": app.client_id, "client_secret": app.client_secret})
    assert response.status_code == 200
    assert response.json()["message"] == "Email verification code sent"
    user.reload()
    response = client.post("/auth/verify-email/verify",data={"email": user.email,"code": user.email_verification_code, "client_id": app.client_id,"client_secret": app.client_secret})
    assert response.status_code == 200
    assert response.json()["message"] == "Email verified"
    # test refresh token
    response = client.post("/auth/refresh",data={"access_token": access_token,"client_id": app.client_id,"client_secret": app.client_secret})
    assert response.status_code == 200
    assert response.json()["access_token"] != None
    access_token = response.json()["access_token"]
    # test access profile of authenticated user
    response = client.get("/auth/me",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["email"] == user.email
    return access_token

@pytest.mark.asyncio
@patch("utils.smsleopard_send_sms")
@patch("utils.mailtrap_send_email")
async def test_permissions_api(mock_send_sms, mock_send_email, client,db):
    mock_send_sms.return_value = True
    mock_send_email.return_value = True
    access_token: str = await authenticate(client,db)
    # test get permissions
    response = client.get("/auth/permissions/",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1
    # test get single permission
    permission_id = str(models.Permission.objects.first().id)
    response = client.get(f"/auth/permissions/{permission_id}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["name"] != None

# test roles api calls
@pytest.mark.asyncio
@patch("utils.smsleopard_send_sms")
@patch("utils.mailtrap_send_email")
@pytest.mark.asyncio
async def test_roles_api(mock_send_sms, mock_send_email,client,db):
    mock_send_sms.return_value = True
    mock_send_email.return_value = True
    access_token: str = await authenticate(client,db)
    # create role
    role_data = {
        "name": "EndUser",
        "description": "End User Role"
    }
    response = client.post("/auth/roles/", json=role_data,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201
    assert response.json()["name"] == "EndUser"
    # get roles
    response = client.get("/auth/roles/",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1
    # get single role
    role_db = models.Role.objects.filter(name="EndUser").first()
    role_id = str(role_db.id)
    response = client.get(f"/auth/roles/{role_id}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == role_db.name
    # update role
    permissions = models.Permission.objects.all()[:3]    
    role_data = {
        "name": "EndUser1",
        "permissions": [{"id":str(p.id)} for p in permissions]
    }
    response = client.put(f"/auth/roles/{role_id}",json=role_data,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "EndUser1"
    assert len(response.json()["permissions"]) == 3
    assert response.json()["permissions"][0]["name"] == permissions[0].name
    # delete role
    response = client.delete(f"/auth/roles/{role_id}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 204
    with pytest.raises(models.Role.DoesNotExist):
        models.Role.objects.get(id=role_id)

# test users api calls
@pytest.mark.asyncio
@patch("utils.smsleopard_send_sms")
@patch("utils.mailtrap_send_email")
async def test_users_api(mock_send_sms, mock_send_email,client,db):
    mock_send_sms.return_value = True
    mock_send_email.return_value = True
    access_token: str = await authenticate(client,db)
    # create user
    user_data = {
        "name": fake.name(),
        "email": fake.unique.email(),
        "phone": fake.unique.phone_number()[0:11],
        "password": fake.password()
    }
    response = client.post("/auth/users/",json=user_data,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201
    assert response.json()["phone"] == user_data["phone"]
    # get users
    response = client.get("/auth/users/",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1
    # get single user
    user_db = models.User.objects.first()
    user_id = str(user_db.id)
    response = client.get(f"/auth/users/{user_id}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["phone"] == user_db.phone
    # update user
    user_id = str(models.User.objects.filter(phone=user_data["phone"]).first().id)
    roles: list[models.Role] = models.Role.objects.all()[:2]
    update_data = {
        "name": fake.name(),
        "email": fake.unique.email(),
        "phone": fake.unique.phone_number()[0:11],
        "roles": [{"id":str(r.id)} for r in roles]
    }
    response = client.put(f"/auth/users/{user_id}",json=update_data,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == update_data["name"]
    assert response.json()["phone"] == update_data["phone"]
    # delete user
    response = client.delete(f"/auth/users/{user_id}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 204
    with pytest.raises(models.User.DoesNotExist):
        models.User.objects.get(id=user_id)

# test clientapps api calls
@pytest.mark.asyncio
@patch("utils.smsleopard_send_sms")
@patch("utils.mailtrap_send_email")
async def test_clientapps_api(mock_send_sms, mock_send_email,client,db):
    mock_send_sms.return_value = True
    mock_send_email.return_value = True
    access_token: str = await authenticate(client,db)
    # create clientapp
    user_db = models.User.objects.first()
    clientapp_data = {
        "name": "Test App",
        "description": "Test App Description",
        "user": {"id": str(user_db.id)}
    }
    response = client.post("/auth/apps/",json=clientapp_data,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201
    assert response.json()["name"] == "Test App"
    # get clientapps
    response = client.get("/auth/apps/",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1
    # get single clientapp
    clientapp_db = models.ClientApp.objects.filter(name="Test App").first()
    clientapp_id = clientapp_db.id
    response = client.get(f"/auth/apps/{str(clientapp_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == clientapp_db.name
    # update clientapp
    update_data = {
        "name": "Test App 1",
        "description": "Test App Description 1",
        "user": {"id": str(user_db.id)} 
    }
    response = client.put(f"/auth/apps/{str(clientapp_id)}",json=update_data,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "Test App 1"
    # delete clientapp
    response = client.delete(f"/auth/apps/{str(clientapp_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 204
    with pytest.raises(models.ClientApp.DoesNotExist):
        models.ClientApp.objects.get(id=clientapp_id)

# test companies api calls
@pytest.mark.asyncio
@patch("utils.smsleopard_send_sms")
@patch("utils.mailtrap_send_email")
async def test_companies_api(mock_send_sms, mock_send_email,client,db):
    mock_send_sms.return_value = True
    mock_send_email.return_value = True
    access_token: str = await authenticate(client,db)
    # create company
    company_data = {
        "name": "Test Company",
        "legal_name": "Test Company Legal Name",
        "description": "Test Company Description",
        "pin_number": str(fake.unique.random_number(6)),
        "nssf_number": str(fake.unique.random_number(6)),
        "shif_number": str(fake.unique.random_number(6)),
        "nita_number": str(fake.unique.random_number(6)),
        "contact_email": fake.unique.email(),
        "contact_phone": fake.unique.phone_number()[0:11],
        "address": fake.address()
    }
    response = client.post("/payroll/companies/",json=company_data,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201
    assert response.json()["name"] == "Test Company"
    # get companies
    response = client.get("/payroll/companies/",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1
    # get single company
    company_db = models.Company.objects.filter(name="Test Company").first()
    company_id = company_db.id
    response = client.get(f"/payroll/companies/{str(company_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == company_db.name
    # update company
    update_data = {
        "name": "Test Company 1",
        "description": "Test Company Description 1"
    }
    response = client.put(f"/payroll/companies/{str(company_id)}",json=update_data,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "Test Company 1"
    # delete company
    response = client.delete(f"/payroll/companies/{str(company_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 204
    with pytest.raises(models.Company.DoesNotExist):
        models.Company.objects.get(id=company_id)

# test staff api calls
@pytest.mark.asyncio
@patch("utils.smsleopard_send_sms")
@patch("utils.mailtrap_send_email")
async def test_staff_api(mock_send_sms, mock_send_email,client,db):
    mock_send_sms.return_value = True
    mock_send_email.return_value = True
    access_token: str = await authenticate(client,db)
    # create staff
    company = models.Company.objects.first()
    user = models.User.objects.first()
    staff_create = {
        "user": {"id": str(user.id)},
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "job_title": fake.job(),
        "department": fake.word(),
        "contact_email": fake.email(),
        "contact_phone": fake.phone_number(),
        "pin_number": str(fake.unique.random_number(6)),
        "staff_number": str(fake.unique.random_number(6)),
        "shif_number": str(fake.unique.random_number(6)),
        "nssf_number": str(fake.unique.random_number(6)),
        "nita_number": str(fake.unique.random_number(6)),
        "national_id_number": str(fake.unique.random_number(6)),
        "date_of_birth": fake.date_of_birth().isoformat(),
        "is_active": True,
        "joined_on": fake.date_time().isoformat()
    }
    response = client.post(f"/payroll/companies/{str(company.id)}/staff/",json=staff_create,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201
    assert response.json()["first_name"] == staff_create["first_name"]
    # get staff
    response = client.get(f"/payroll/companies/{str(company.id)}/staff/",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1
    # get single staff
    staff_db = models.Staff.objects.filter(first_name=staff_create["first_name"]).first()
    staff_id = staff_db.id
    response = client.get(f"/payroll/companies/{str(company.id)}/staff/{str(staff_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["first_name"] == staff_db.first_name
    # update staff
    update_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "job_title": fake.job(),
        "department": fake.word(),
        "contact_email": fake.email(),
        "contact_phone": fake.phone_number(),
        "pin_number": str(fake.unique.random_number(6)),
        "staff_number": str(fake.unique.random_number(6)),
        "shif_number": str(fake.unique.random_number(6)),
        "nssf_number": str(fake.unique.random_number(6)),
        "nita_number": str(fake.unique.random_number(6)),
        "national_id_number": str(fake.unique.random_number(6)),
        "date_of_birth": fake.date_of_birth().isoformat(),
        "is_active": True,
        "joined_on": fake.date_time().isoformat()
    }
    response = client.put(f"/payroll/companies/{str(company.id)}/staff/{str(staff_id)}",json=update_data,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["first_name"] == update_data["first_name"]
    # delete staff
    response = client.delete(f"/payroll/companies/{str(company.id)}/staff/{str(staff_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 204
    with pytest.raises(models.Staff.DoesNotExist):
        models.Staff.objects.get(id=staff_id)

# test bands api calls
@pytest.mark.asyncio
@patch("utils.smsleopard_send_sms")
@patch("utils.mailtrap_send_email")
async def test_bands_api(mock_send_sms, mock_send_email,client,db):
    mock_send_sms.return_value = True
    mock_send_email.return_value = True
    access_token: str = await authenticate(client,db)
    # create band
    band_create = {
        "period_start": fake.date_time_this_year().isoformat(),
        "period_end": fake.date_time_this_year().isoformat(),
        "band_type": "PAYE",
        "band_frequency": "monthly",
        "lower": 0,
        "upper": 24000,
        "rate": 0.1
    }
    response = client.post("/payroll/bands/",json=band_create,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201
    assert response.json()["band_type"] == "PAYE"
    # get bands
    response = client.get("/payroll/bands/",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1
    # get single band
    band_db = models.Band.objects.filter(upper=24000).first()
    band_id = band_db.id
    response = client.get(f"/payroll/bands/{str(band_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["lower"] == str(band_db.lower)
    assert response.json()["upper"] == str(band_db.upper)
    # update band
    band_update = {
        "period_start": fake.date_time_this_year().isoformat(),
        "period_end": fake.date_time_this_year().isoformat(),
        "band_type": "NSSF",
        "band_frequency": "monthly",
        "lower": 0,
        "upper": 24000,
        "rate": 0.1
    }
    response = client.put(f"/payroll/bands/{str(band_id)}",json=band_update,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["band_type"] == "NSSF"
    # delete band
    response = client.delete(f"/payroll/bands/{str(band_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 204
    with pytest.raises(models.Band.DoesNotExist):
        models.Band.objects.get(id=band_id)


# test PayrollCodes api calls
@pytest.mark.asyncio
@patch("utils.smsleopard_send_sms")
@patch("utils.mailtrap_send_email")
async def test_payrollcodes_api(mock_send_sms, mock_send_email,client,db):
    mock_send_sms.return_value = True
    mock_send_email.return_value = True
    access_token: str = await authenticate(client,db)
    # create payrollcode
    company = models.Company.objects.first()
    payrollcode_create = {
        "name": "BASE",
        "description": "Base Salary",
        "variable": "base_salary",
        "code_type": "input",
        "value": 1000,
        "tags": ["COMPENSATION"],
        "formula":"",
        "order": 1,
        "effective_from": fake.date_time_this_year().isoformat()
    }
    response = client.post(f"/payroll/companies/{str(company.id)}/codes/",json=payrollcode_create,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201
    assert response.json()["name"] == "BASE"
    # get payrollcodes
    response = client.get(f"/payroll/companies/{str(company.id)}/codes/",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1
    # get single payrollcode
    payrollcode_db = models.PayrollCode.objects.filter(name="BASE").first()
    payrollcode_id = payrollcode_db.id
    response = client.get(f"/payroll/companies/{str(company.id)}/codes/{str(payrollcode_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == payrollcode_db.name
    # update payrollcode
    payrollcode_update = {
        "name": "BASE2",
        "description": "Base Salary",
        "variable": "base_salary",
        "code_type": "input",
        "value": 1000,
        "tags": ["COMPENSATION"],
        "formula":"",
        "order": 1,
        "effective_from": fake.date_time_this_year().isoformat()
    }
    response = client.put(f"/payroll/companies/{str(company.id)}/codes/{str(payrollcode_id)}",json=payrollcode_update,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "BASE2"
    # delete payrollcode
    response = client.delete(f"/payroll/companies/{str(company.id)}/codes/{str(payrollcode_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 204
    with pytest.raises(models.PayrollCode.DoesNotExist):
        models.PayrollCode.objects.get(id=payrollcode_id)

# test Computations api calls
@pytest.mark.asyncio
@patch("utils.smsleopard_send_sms")
@patch("utils.mailtrap_send_email")
async def test_computations_api(mock_send_sms, mock_send_email,client,db):
    mock_send_sms.return_value = True
    mock_send_email.return_value = True
    access_token: str = await authenticate(client,db)
    # create computation
    # get company with at least one staff and payrollcode
    company_db = models.Company.objects.filter(name="Test Company1").first()
    user = models.User.objects.first()
    computation_create = {
        "payroll_period_start": datetime.datetime(2025,3,1,0,0,0,0,tzinfo=datetime.timezone.utc).isoformat(),
        "payroll_period_end": datetime.datetime(2025,3,31,0,0,0,0,tzinfo=datetime.timezone.utc).isoformat(),
        "notes": "Test Computation",
        "status": "draft",
        "generated_by": {"id": str(user.id)}
    }
    response = client.post(f"/payroll/companies/{str(company_db.id)}/computations/",json=computation_create,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201
    assert response.json()["notes"] == "Test Computation"
    # get computations
    response = client.get(f"/payroll/companies/{str(company_db.id)}/computations/",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1
    # get single computation
    computation_db = models.Computation.objects.filter(notes="Test Computation").first()
    computation_id = computation_db.id
    response = client.get(f"/payroll/companies/{str(company_db.id)}/computations/{str(computation_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["notes"] == computation_db.notes
    # update computation
    computation_update = {
        "payroll_period_start": fake.date_time_this_year().isoformat(),
        "payroll_period_end": fake.date_time_this_year().isoformat(),
        "notes": "Test Computation 1",
        "status": "draft",
        "generated_by": {"id": str(user.id)}
    }
    response = client.put(f"/payroll/companies/{str(company_db.id)}/computations/{str(computation_id)}",json=computation_update,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["notes"] == "Test Computation 1"
    # get compensation template 
    response = client.get(f"/payroll/companies/{str(company_db.id)}/computations/{str(computation_id)}/compensation-template",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["url"] != None
    url = response.json()["url"]
    # download compensation template
    response = client.get(url, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    with open("temp_file.xlsx", "wb") as f:
        f.write(response.content)
    df = pd.read_excel("temp_file.xlsx",sheet_name="Sheet1")
    assert df.columns.tolist() == ['staff_number', 'basic_salary']
    if os.path.exists("temp_file.xlsx"):
        os.remove("temp_file.xlsx")
    # upload compensation data
    output = io.BytesIO()
    staff_db = models.Staff.objects.filter(company = computation_db.company).first()
    staff_number = staff_db.staff_number
    df.loc[len(df)] = [staff_number,500_000]
    # validations
    # df.columns = ['staff_number1', 'basic_salary']
    # df.columns = ['staff_number', 'basic_salary1']
    # df.loc[len(df)] = ["staff_number",500_000]
    df.to_excel(output, index=False)
    output.seek(0)
    response = client.post(
        url=f"/payroll/companies/{str(company_db.id)}/computations/{str(computation_id)}/upload-compensation",
        files={"file": ("test_file.xlsx", output, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert response.json()[0]["computation"]["id"] == str(computation_id)
    assert response.json()[0]["staff"]["id"] == str(staff_db.id)
    assert response.json()[0]["value"] == "500000.00"
    # run computation getting streaming response
    response = client.post(f"/payroll/companies/{str(company_db.id)}/computations/{str(computation_id)}/run",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"
    for line in response.iter_lines():
        data = json.loads(line)
        assert data["staff"] != None
        assert data["payroll"] != None
        assert data["payroll"]["basic_salary"] == 500_000
        assert data["payroll"]["tax"] == 50_000

    # generate payslips
    response = client.post(f"/reports/computations/{str(computation_id)}/generate-payslips",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"
    for line in response.iter_lines():
        data = json.loads(line)
        assert data["staff"] != None
        assert data["payslip_url"] != None
    payslip_url = data["payslip_url"]
    # download payslip
    response = client.get(payslip_url,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.content != None
    assert response.headers["content-type"] == "application/pdf"

    # generate p9as
    year = computation_db.payroll_period_start.year
    period_start = datetime.datetime(year,1,1,0,0,0,0,tzinfo=datetime.timezone.utc)
    period_end = datetime.datetime(year,12,31,0,0,0,0,tzinfo=datetime.timezone.utc)
    period_filter = f"?period_start={period_start.strftime('%Y-%m-%d %H:%M:%S')}&period_end={period_end.strftime('%Y-%m-%d %H:%M:%S')}" 
    response = client.post(f"/reports/p9as/companies/{str(computation_db.company.id)}/generate{period_filter}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"
    for line in response.iter_lines():
        data = json.loads(line)
        assert data["staff"] != None
        assert data["p9a_url"] != None
    p9a_url = data["p9a_url"]
    # download p9a
    response = client.get(p9a_url,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.content != None
    assert response.headers["content-type"] == "application/pdf"
    # generate company summary
    response = client.post(f"/reports/computations/{str(computation_id)}/generate-payroll-report",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["url"] != None
    # download company summary
    company_summary_url = response.json()["url"]
    response = client.get(company_summary_url,headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.content != None
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    # delete computation
    response = client.delete(f"/payroll/companies/{str(company_db.id)}/computations/{str(computation_id)}",headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 204
    with pytest.raises(models.Computation.DoesNotExist):
        models.Computation.objects.get(id=computation_id)    