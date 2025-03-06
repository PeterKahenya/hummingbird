from bdb import effective
import os
import shutil
from fastapi.testclient import TestClient
from pydantic_settings import BaseSettings
import pytest
import mongomock
from mongoengine import connect
import models
import faker
import bson
import utils
from datetime import datetime, timedelta, timezone
import random

fake = faker.Faker()

class AppSettings(BaseSettings):
    superuser_phone: str = "0711111111"
    superuser_email: str = "test@example.com"
    superuser_password: str = "password"
    mongodb_password: str = "example"
    mongodb_host: str = "localhost"
    mongodb_port: str = "27017"
    mongodb_database: str = "mongoenginetest"

settings = AppSettings()

def seed_db() -> None:
    for _ in range(5):
        content_in_db = models.ContentType(
            model=fake.word(),
            object_id=bson.ObjectId(),  # This is correct
            type_of_content="specific_object"
        )
        content_in_db.save()
        permission_in_db = models.Permission(
            name=fake.word(),
            codename=fake.word(),
            content_type=content_in_db
        )
        permission_in_db.save()
        role_in_db = models.Role(
            name=fake.word(),
            description = fake.sentence(),
            permissions=[permission_in_db]
        )
        role_in_db.save()
        user_in_db = models.User(
            name = fake.name(),
            phone = fake.phone_number(),
            email = fake.email(),
            password = fake.password(),
            is_active = True,
            last_seen = fake.date_time_this_year(),
            phone_verification_code = utils.generate_random_string(6),
            phone_verification_code_expiry = fake.date_time_this_year()+fake.time_delta(),
            is_verified = True,
            roles = [role_in_db]
        )
        user_in_db.save()
        client_app = models.ClientApp(
            name = fake.company(),
            description = fake.sentence(),
            client_id = utils.generate_client_id(),
            client_secret = utils.generate_client_secret(),
            user = user_in_db
        )
        client_app.save()
        company = models.Company(
            name="Test Company1",
            legal_name=fake.company() + " Ltd.",
            description=fake.text(),
            pin_number = utils.generate_random_string(10),
            nssf_number=utils.generate_random_string(8),
            shif_number=utils.generate_random_string(8),
            nita_number=utils.generate_random_string(8),
            contact_email=fake.company_email(),
            contact_phone=fake.phone_number(),
            address=fake.address()
        )
        company.save()
        staff = models.Staff(
            user=user_in_db,
            company=company,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            job_title=fake.job(),
            department=fake.word(),
            contact_email=fake.email(),
            contact_phone=fake.phone_number(),
            pin_number = utils.generate_random_string(10),
            staff_number = utils.generate_random_string(6),
            shif_number = utils.generate_random_string(6),
            nssf_number = utils.generate_random_string(6),
            nita_number = utils.generate_random_string(6),
            national_id_number = utils.generate_random_string(8),
            date_of_birth = fake.date_time_this_century(),
            is_active = True,
            joined_on = fake.date_time_this_year(),
            departed_on = None,
            bank_account_number = utils.generate_random_string(10),
            bank_name = fake.company(),
            bank_swift_code = utils.generate_random_string(8),
            bank_branch = fake.word()
        )
        staff.save()
        band_paye = models.Band(
            period_start=datetime.now(tz=timezone.utc),
            period_end=datetime.now(tz=timezone.utc) + timedelta(days=365),
            band_type="PAYE",
            band_frequency="monthly",
            lower=random.uniform(1000, 5000),
            upper=random.uniform(5001, 20000),
            rate=random.uniform(5, 30)
        )
        band_paye.save()
        band_nssf = models.Band(
            period_start=datetime.now(tz=timezone.utc),
            period_end=datetime.now(tz=timezone.utc) + timedelta(days=365),
            band_type="NSSF",
            band_frequency="monthly",
            lower=random.uniform(500, 3000),
            upper=random.uniform(3001, 10000),
            rate=random.uniform(3, 10)
        )
        band_nssf.save()
        payroll_code_fixed = models.PayrollCode(
            company=company,
            name="Basic Salary",
            description="Fixed base salary",
            variable="basic_salary",
            code_type="input",
            tags = ["BASIC", "COMP"],
            value=random.uniform(30000, 100000),
            formula="",
            order=1,
            effective_from=datetime(2025,1,1,tzinfo=timezone.utc)
        )
        payroll_code_fixed.save()
        payroll_code_formula = models.PayrollCode(
            company=company,
            name="Tax",
            description="Calculated tax",
            variable="tax",
            code_type="formula",
            tags=["TAX","DED"],
            value=0.0,
            formula="basic_salary * 0.1",
            order=2,
            effective_from=datetime(2025,1,1,tzinfo=timezone.utc)
        )
        payroll_code_formula.save()
        payroll_code_net_pay = models.PayrollCode(
            company=company,
            name="Net Pay",
            description="Calculated net pay",
            variable="net_pay",
            code_type="formula",
            tags=["NET"],
            value=0.0,
            formula="basic_salary - tax",
            order=3,
            effective_from=datetime(2025,1,1,tzinfo=timezone.utc)
        )
        payroll_code_net_pay.save()
        computation = models.Computation(
            company=company,
            notes=fake.sentence(),
            payroll_period_start=datetime.now(tz=timezone.utc) - timedelta(days=30),
            payroll_period_end=datetime.now(tz=timezone.utc),
            status="draft",
            generated_by=user_in_db
        )
        computation.save()
        computation_component = models.ComputationComponent(
            computation=computation,
            payroll_component=payroll_code_fixed,
            staff=staff,
            value=payroll_code_fixed.value
        )
        computation_component.save()
        computation_component_tax = models.ComputationComponent(
            computation=computation,
            payroll_component=payroll_code_formula,
            staff=staff,
            value=payroll_code_formula.value if payroll_code_formula.value else 0.0
        )
        computation_component_tax.save()

@pytest.fixture(scope="session")
def db():
    shutil.copytree("templates/Master Company", "templates/Test Company1", dirs_exist_ok=True)
    connect('mongoenginetest', host='mongodb://localhost', mongo_client_class=mongomock.MongoClient, uuidRepresentation="standard")
    utils.initialize_db(settings, is_test=True)
    seed_db()
    yield
    shutil.rmtree("templates/Test Company1", ignore_errors=True)
    shutil.rmtree("reports/Test Company1", ignore_errors=True)

@pytest.fixture(scope="session")
def client():
    from api import app
    from depends import get_db
    def get_test_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = get_test_db
    yield TestClient(app)