import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# Ensure all ORM models are registered on Base.metadata before create_all.
from app.modules.ai.models import AIConversation, AIMessage, AIUsage  # noqa: F401
from app.modules.auth.models import RefreshToken  # noqa: F401
from app.modules.customers.models import Customer  # noqa: F401
from app.modules.orders.models import Order, OrderItem  # noqa: F401
from app.modules.organizations.models import Organization, OrganizationMember  # noqa: F401
from app.modules.products.models import Product  # noqa: F401
from app.modules.reports.models import Report  # noqa: F401
from app.modules.tasks.models import Task  # noqa: F401
from app.modules.users.models import User  # noqa: F401


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_factory() as session:
        yield session

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest.fixture
async def client(db_session) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
