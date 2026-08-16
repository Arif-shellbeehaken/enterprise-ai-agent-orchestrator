"""
Shared pytest fixtures – in-memory SQLite for isolation, no external Postgres required.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Ensure app packages are importable
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.main import app
from app.models.user import User
from app.models.agent import Agent


# ---------------------------------------------------------------------------
# Event loop (pytest-asyncio handles most of this; keep explicit for clarity)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# In-memory async SQLite engine (shared connection for StaticPool)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with DB dependency overridden to the test session."""

    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

TENANT_ID = uuid4()
ADMIN_ID = uuid4()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=ADMIN_ID,
        tenant_id=TENANT_ID,
        email="admin@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="Admin",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def operator_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        tenant_id=TENANT_ID,
        email="operator@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="Operator",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def sample_agent(db_session: AsyncSession, admin_user: User) -> Agent:
    agent = Agent(
        id=uuid4(),
        tenant_id=admin_user.tenant_id,
        name="Test Ops Agent",
        description="Fixture agent",
        system_prompt="You are a careful enterprise agent. Never transfer funds without approval.",
        model_name="gemini-2.0-flash",
        requires_approval=True,
        approval_threshold_usd=100.00,
    )
    db_session.add(agent)
    await db_session.flush()
    return agent


def auth_header(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )
    return {"Authorization": f"Bearer {token}"}
