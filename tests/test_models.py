import models
import bson
import faker

pytest_plugins = ('pytest_asyncio',)
fake = faker.Faker()

def test_auth_models(db: None) -> None:
    content_type = models.ContentType(model="auth", object_id=bson.ObjectId(), type_of_content="specific_object")
    content_type.save()
    assert content_type.id is not None
    permission = models.Permission(name="auth", codename="auth", content_type=content_type)
    permission.save()
    assert permission.id is not None
    role = models.Role(name="auth", permissions=[permission])
    role.save()
    assert role.id is not None
    user = models.User(
        name=fake.name(),
        phone=fake.phone_number(),
        email=fake.email(),
        is_active=True,
        last_seen=fake.date_time_this_year(),
        phone_verification_code="auth",
        phone_verification_code_expiry=fake.date_time_this_year()+fake.time_delta(),
        is_verified=True,
        roles=[role]
    )
    user.save()
    assert user.id is not None
    client_app = models.ClientApp(
        name="auth",
        description="auth",
        user=user
    )
    client_app.save()
    assert client_app.id is not None

def test_payroll_models(db):
    band = models.Band(
        period_start=fake.date_time_this_year(), 
        period_end=fake.date_time_this_year(),
        band_type="PAYE",
        band_frequency="monthly",
        lower = 0,
        upper = 24000,
        rate = 0.1
    )
    band.save()
    assert band.id is not None

    company = models.Company(
        name=fake.company(),
        legal_name=fake.company() + " Ltd.",
        description=fake.text(),
        pin_number = "auth",
        nssf_number="auth",
        shif_number="auth",
        nita_number="auth",
        contact_email=fake.company_email(),
        contact_phone=fake.phone_number(),
        address=fake.address()
    )
    company.save()
    assert company.id is not None

    staff = models.Staff(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        job_title=fake.job(),
        department=fake.word(),
        contact_email=fake.email(),
        contact_phone=fake.phone_number(),
        pin_number = "auth",
        staff_number = "auth",
        company=company
    )
    staff.save()
    assert staff.id is not None

    payroll_code = models.PayrollCode(
        company=company,
        name="BASE PAY",
        description="Base Pay",
        variable="base_pay",
        code_type="input",
        tags=["COMPENSATION"],
        value=0,
        formula="",
        order=1,
        effective_from=fake.date_time_this_year(),
    )
    payroll_code.save()
    assert payroll_code.id is not None

    computation = models.Computation(
        company = company,
        notes = fake.text(),
        payroll_period_start = fake.date_time_this_year(),
        payroll_period_end = fake.date_time_this_year(),
        status = "draft",
        generated_by = models.User.objects.first(),
    )
    computation.save()
    assert computation.id is not None

    computation_component = models.ComputationComponent(
        computation = computation,
        payroll_component = payroll_code,
        staff = staff,
        value = 500_000
    )
    computation_component.save()
    assert computation_component.id is not None