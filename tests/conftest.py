from openpyxl import formula
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
            name=fake.company(),
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
            code_type="fixed",
            value=random.uniform(30000, 100000),
            formula="",
            order=1
        )
        payroll_code_fixed.save()
        payroll_code_formula = models.PayrollCode(
            company=company,
            name="Tax",
            description="Calculated tax",
            variable="tax",
            code_type="formula",
            tags=["TAX"],
            value=0.0,
            formula="params['Basic Salary'] * 0.1",
            order=2
        )
        payroll_code_formula.save()
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
    print("Database seeded successfully!")



@pytest.fixture(scope="session")
def db() -> None:
    connect('mongoenginetest', host='mongodb://localhost', mongo_client_class=mongomock.MongoClient, uuidRepresentation="standard")
    seed_db()
    # yield

    
# @pytest.fixture(scope="session")
# def client(db):
#     def get_test_db():
#         try:
#             yield db
#         finally:
#             pass
#     app.dependency_overrides[get_db] = get_test_db
#     yield TestClient(app)