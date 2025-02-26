import crud
import models
import schemas
import pytest
import faker
import bson

# create a faker instance
fake = faker.Faker()
pytest_plugins = ('pytest_asyncio',)

# test get_obj_or_404
@pytest.mark.asyncio
async def test_get_obj_or_404(db):
    company_id = models.Company.objects.first().id
    company_id = str(company_id)
    company = await crud.get_obj_or_404(models.Company, company_id)
    assert company is not None
    assert str(company.id) == company_id
    with pytest.raises(models.Company.DoesNotExist):
        await crud.get_obj_or_404(models.Company, str(bson.ObjectId()))
    with pytest.raises(bson.errors.InvalidId):
        await crud.get_obj_or_404(models.Company, "1234567890")

# test get_obj_or_None
@pytest.mark.asyncio
async def test_get_obj_or_None(db):
    company_id = models.Company.objects.first().id
    company_id = str(company_id)
    company = await crud.get_obj_or_None(models.Company, company_id)
    assert company is not None
    assert str(company.id) == company_id
    company = await crud.get_obj_or_None(models.Company, str(bson.ObjectId()))
    assert company is None

# test filter_objs using User model
@pytest.mark.asyncio
async def test_filter_objs(db):
    params = {
        "name__icontains": "a",
        "is_active": True,
        "email__icontains": "@",
        "phone__icontains": "7"
    }
    users = await crud.filter_objs(models.User, params, sort_by="name,asc")
    assert users is not None
    for user in users:
        assert "a" in user.name.lower()
        assert user.is_active
        assert "@" in user.email
        assert "7" in user.phone
    with pytest.raises(AttributeError):
        await crud.filter_objs(models.User, {"invalid": "a"})

# test search_objs using User model
@pytest.mark.asyncio
async def test_search_objs(db):
    users = await crud.search_objs(models.User, "a")
    assert users is not None
    assert all("a" in user.name.lower() or "a" in user.email.lower() for user in users)
    users = await crud.search_objs(models.User, "ricardo shilly shally")
    assert users is not None
    assert len(users) == 0

# test create_obj using User model
@pytest.mark.asyncio
async def test_create_obj(db):
    user_create = schemas.UserCreate(**{
        "phone": "9994567890",
        "name": "Test User",
        "password": "testpassword",
        "email": "test@test.com",
    })
    user_db = await crud.create_obj(models.User, user_create)
    assert user_db is not None
    assert user_db.id is not None
    assert user_db.phone == "9994567890"
    assert user_db.name == "Test User"

# test update_obj using User model
@pytest.mark.asyncio
async def test_update_obj(db):
    user_id = models.User.objects.first().id
    user_id = str(user_id)
    fake_phone = fake.phone_number()
    user_update = schemas.UserUpdate(**{
        "phone": fake_phone,
        "name": "Test User Updated"
    })
    user_db = await crud.update_obj(models.User, user_id, user_update)
    assert user_db is not None
    assert str(user_db.id) == user_id
    assert user_db.phone == fake_phone
    assert user_db.name == "Test User Updated"
    with pytest.raises(models.User.DoesNotExist):
        await crud.update_obj(models.User, str(bson.ObjectId()), user_update)

# test delete_obj using User model
@pytest.mark.asyncio
async def test_delete_obj(db):
    user = models.User(
        phone="7994567890",
        name="Test User",
        password="testpassword",
        email="test2@mail.africa"
    )
    user.save()
    user_id = user.id
    user_id = str(user_id)
    resp = await crud.delete_obj(models.User, user_id)
    assert resp is None
    with pytest.raises(models.User.DoesNotExist):
        await crud.delete_obj(models.User, str(bson.ObjectId()))

# test pagination
@pytest.mark.asyncio
async def test_pagination(db):
    # create 100 users
    previous_users = models.User.objects.all()
    for i in range(100):
        user_create = schemas.UserCreate(**{
            "phone": f"29456789{i}",
            "name": f"Test Paginate User{i}",
            "password": "testpassword",
            "email": fake.email()            
        })
        user_db = await crud.create_obj(models.User, user_create)
    users = models.User.objects.all()
    # test pagination
    users = await crud.paginate(models.User, schemas.UserInDB, page=1, size=30,params={},q="paginate")
    assert len(users.data) == 30
    users = await crud.paginate(models.User, schemas.UserInDB, page=2, size=20,params={},q="paginate")
    assert len(users.data) == 20

# test payroll concert
@pytest.mark.asyncio
async def test_payroll_concert(db):
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
    company = await crud.create_obj(models.Company, company_create)
    staff_create = schemas.StaffCreate(**{
        "user": str(models.User.objects.first().id),
        "company": str(company.id),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "job_title": fake.job(),
        "contact_email": fake.company_email(),
        "pin_number": "auth",
        "staff_number": "auth",
        "national_id_number": "auth"
    })
    staff = await crud.create_obj(models.Staff, staff_create)
    assert staff is not None
    payroll_code_create_basic_salary = schemas.PayrollCodeCreate(**{
        "company": str(company.id),
        "name": "Basic Salary",
        "description": "Basic salary input",
        "variable": "basic_salary",
        "code_type": "input",
        "value": 0,
        "formula": "",
        "tags": ["COMP"],
        "order": 1,
        "effective_from": "2021-01-01T00:00:00"
    })
    payroll_code_basic_salary = await crud.create_obj(models.PayrollCode, payroll_code_create_basic_salary)
    payroll_code_create_tax = schemas.PayrollCodeCreate(**{
        "company": str(company.id),
        "name": "Tax",
        "description": "Calculated tax",
        "variable": "tax",
        "code_type": "formula",
        "value": 0.0,
        "formula": "basic_salary * 0.1",
        "tags": ["DED"],
        "order": 2,
        "effective_from": "2021-01-01T00:00:00"
    })
    payroll_code_tax = await crud.create_obj(models.PayrollCode, payroll_code_create_tax)
    computation_create = schemas.ComputationCreate(**{
        "company": str(company.id),
        "notes": "Test computation",
        "payroll_period_start": "2021-01-01T00:00:00",
        "payroll_period_end": "2021-01-31T23:59:59",
        "status": "draft",
        "generated_by": str(staff.id)
    })
    computation = await crud.create_obj(models.Computation, computation_create)
    assert computation is not None
    assert computation.id is not None
    computation_component_create_basic_salary = schemas.ComputationComponentCreate(**{
        "computation": str(computation.id),
        "payroll_component": str(payroll_code_basic_salary.id),
        "staff": str(staff.id),
        "value": 500_000.0
    })
    await crud.create_obj(models.ComputationComponent, computation_component_create_basic_salary)
    comps = computation.run()
    staff, payroll = next(comps)
    assert staff is not None
    assert payroll is not None
    assert payroll["tax"] == 50_000.0
    assert payroll["basic_salary"] == 500_000.0