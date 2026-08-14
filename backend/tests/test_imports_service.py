import json
import uuid

import pytest
from sqlalchemy import select

from app.modules.customers.models import Customer
from app.modules.imports import service as imports_service
from app.modules.imports.models import ImportStatus, ImportType
from app.modules.organizations.models import Organization
from app.modules.products.models import Product
from app.shared.exceptions import ValidationAppError


async def _make_org(db_session) -> uuid.UUID:
    org = Organization(id=uuid.uuid4(), name="Acme")
    db_session.add(org)
    await db_session.commit()
    return org.id


async def test_valid_customers_csv_imports_all_rows(db_session):
    org_id = await _make_org(db_session)
    csv_content = (
        "name,email,status\n"
        "Alice Alpha,alice@customer.example,active\n"
        "Bob Beta,bob@customer.example,at_risk\n"
    )
    job = await imports_service.create_import_job(
        db_session, org_id, None, ImportType.CUSTOMERS, "customers.csv", csv_content
    )
    await imports_service.run_import_job(db_session, job.id)

    refreshed = await imports_service.get_import_job(db_session, org_id, job.id)
    assert refreshed.status == ImportStatus.COMPLETED
    assert refreshed.total_rows == 2
    assert refreshed.imported_rows == 2
    assert refreshed.failed_rows == 0

    customers = (
        (await db_session.execute(select(Customer).where(Customer.organization_id == org_id)))
        .scalars()
        .all()
    )
    assert {c.name for c in customers} == {"Alice Alpha", "Bob Beta"}


async def test_valid_products_csv_imports_all_rows(db_session):
    org_id = await _make_org(db_session)
    csv_content = (
        "name,category,price,active\n"
        "Widget,Hardware,19.99,true\n"
        "Gadget,Electronics,49.99,false\n"
    )
    job = await imports_service.create_import_job(
        db_session, org_id, None, ImportType.PRODUCTS, "products.csv", csv_content
    )
    await imports_service.run_import_job(db_session, job.id)

    refreshed = await imports_service.get_import_job(db_session, org_id, job.id)
    assert refreshed.status == ImportStatus.COMPLETED
    assert refreshed.imported_rows == 2

    products = (
        (await db_session.execute(select(Product).where(Product.organization_id == org_id)))
        .scalars()
        .all()
    )
    assert {p.name for p in products} == {"Widget", "Gadget"}
    gadget = next(p for p in products if p.name == "Gadget")
    assert gadget.active is False


async def test_invalid_row_is_skipped_with_error_recorded(db_session):
    org_id = await _make_org(db_session)
    csv_content = (
        "name,email,status\n"
        "Good Customer,good@customer.example,active\n"
        "Bad Customer,not-an-email,active\n"
    )
    job = await imports_service.create_import_job(
        db_session, org_id, None, ImportType.CUSTOMERS, "customers.csv", csv_content
    )
    await imports_service.run_import_job(db_session, job.id)

    refreshed = await imports_service.get_import_job(db_session, org_id, job.id)
    assert refreshed.status == ImportStatus.COMPLETED
    assert refreshed.total_rows == 2
    assert refreshed.imported_rows == 1
    assert refreshed.failed_rows == 1

    errors = json.loads(refreshed.errors)
    assert len(errors) == 1
    assert errors[0]["row"] == 3

    customers = (
        (await db_session.execute(select(Customer).where(Customer.organization_id == org_id)))
        .scalars()
        .all()
    )
    assert len(customers) == 1
    assert customers[0].name == "Good Customer"


async def test_duplicate_email_upserts_instead_of_duplicating(db_session):
    org_id = await _make_org(db_session)
    csv_content = (
        "name,email,status\n"
        "First Name,dupe@customer.example,active\n"
        "Updated Name,dupe@customer.example,at_risk\n"
    )
    job = await imports_service.create_import_job(
        db_session, org_id, None, ImportType.CUSTOMERS, "customers.csv", csv_content
    )
    await imports_service.run_import_job(db_session, job.id)

    customers = (
        (await db_session.execute(select(Customer).where(Customer.organization_id == org_id)))
        .scalars()
        .all()
    )
    assert len(customers) == 1
    assert customers[0].name == "Updated Name"
    assert customers[0].status.value == "at_risk"


async def test_malformed_csv_missing_required_columns_fails_whole_job(db_session):
    org_id = await _make_org(db_session)
    csv_content = "not_a_valid_header\nsome,garbage,data\n"
    job = await imports_service.create_import_job(
        db_session, org_id, None, ImportType.CUSTOMERS, "customers.csv", csv_content
    )
    await imports_service.run_import_job(db_session, job.id)

    refreshed = await imports_service.get_import_job(db_session, org_id, job.id)
    assert refreshed.status == ImportStatus.FAILED
    assert refreshed.completed_at is not None


async def test_rejects_non_csv_filename(db_session):
    org_id = await _make_org(db_session)
    with pytest.raises(ValidationAppError) as exc_info:
        await imports_service.create_import_job(
            db_session, org_id, None, ImportType.CUSTOMERS, "customers.txt", "name,email\n"
        )
    assert exc_info.value.code == "INVALID_FILE_TYPE"


async def test_rejects_oversized_file(db_session):
    org_id = await _make_org(db_session)
    huge_content = "name,email\n" + ("a,b@example.com\n" * 1_000_000)
    with pytest.raises(ValidationAppError) as exc_info:
        await imports_service.create_import_job(
            db_session, org_id, None, ImportType.CUSTOMERS, "customers.csv", huge_content
        )
    assert exc_info.value.code == "FILE_TOO_LARGE"
