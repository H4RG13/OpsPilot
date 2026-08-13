import uuid
from datetime import date, timedelta

import pytest

from app.modules.ai.tools.registry import execute_tool
from app.modules.customers.models import Customer, CustomerStatus
from app.modules.organizations.models import Organization
from app.shared.exceptions import AppError


async def _make_org(db_session) -> uuid.UUID:
    org = Organization(id=uuid.uuid4(), name="Test Org")
    db_session.add(org)
    await db_session.commit()
    return org.id


async def _make_customer(
    db_session, organization_id, name="Jane Doe", status=CustomerStatus.ACTIVE
):
    customer = Customer(
        id=uuid.uuid4(),
        organization_id=organization_id,
        name=name,
        email=f"{name.lower().replace(' ', '.')}@example.com",
        status=status,
        lifetime_value=100,
    )
    db_session.add(customer)
    await db_session.commit()
    return customer


async def test_get_revenue_summary_returns_zero_for_empty_org(db_session):
    org_id = await _make_org(db_session)
    result = await execute_tool(
        db_session,
        org_id,
        "get_revenue_summary",
        {"start_date": "2026-01-01", "end_date": "2026-01-31"},
    )
    assert result["revenue"] == "0.00"
    assert result["order_count"] == 0


async def test_search_customers_scoped_to_organization(db_session):
    org_a = await _make_org(db_session)
    org_b = await _make_org(db_session)
    await _make_customer(db_session, org_a, name="Alice Alpha")
    await _make_customer(db_session, org_b, name="Alice Beta")

    result = await execute_tool(
        db_session, org_a, "search_customers", {"query": "Alice", "limit": 10}
    )
    assert len(result) == 1
    assert result[0]["name"] == "Alice Alpha"


async def test_get_at_risk_customers_filters_by_status(db_session):
    org_id = await _make_org(db_session)
    await _make_customer(db_session, org_id, name="Active Customer", status=CustomerStatus.ACTIVE)
    await _make_customer(db_session, org_id, name="Risky Customer", status=CustomerStatus.AT_RISK)

    result = await execute_tool(db_session, org_id, "get_at_risk_customers", {"limit": 10})
    assert len(result) == 1
    assert result[0]["name"] == "Risky Customer"


async def test_unknown_tool_raises_app_error(db_session):
    with pytest.raises(AppError) as exc_info:
        await execute_tool(db_session, uuid.uuid4(), "delete_everything", {})
    assert exc_info.value.code == "UNKNOWN_TOOL"


async def test_invalid_arguments_raise_app_error(db_session):
    with pytest.raises(AppError) as exc_info:
        await execute_tool(
            db_session, uuid.uuid4(), "get_revenue_summary", {"start_date": "not-a-date"}
        )
    assert exc_info.value.code == "INVALID_TOOL_ARGUMENTS"


async def test_compare_revenue_returns_both_periods(db_session):
    org_id = await _make_org(db_session)
    today = date.today()
    result = await execute_tool(
        db_session,
        org_id,
        "compare_revenue",
        {
            "period_a_start": (today - timedelta(days=7)).isoformat(),
            "period_a_end": today.isoformat(),
            "period_b_start": (today - timedelta(days=14)).isoformat(),
            "period_b_end": (today - timedelta(days=8)).isoformat(),
        },
    )
    assert "period_a" in result
    assert "period_b" in result
    assert result["change_pct"] is None
