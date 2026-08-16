"""
Async SQLAlchemy engine and session factory for PostgreSQL.
Engine is created lazily so unit tests can override without asyncpg.
"""

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        kwargs = {
            "echo": settings.DB_ECHO,
            "pool_pre_ping": True,
        }
        # pool_size / max_overflow only valid for non-SQLite
        if not settings.DATABASE_URL.startswith("sqlite"):
            kwargs["pool_size"] = settings.DB_POOL_SIZE
            kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        _engine = create_async_engine(settings.DATABASE_URL, **kwargs)
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()  # ensure created
    assert _session_factory is not None
    return _session_factory


# Backwards-compatible module-level accessors used by main.py
@property  # type: ignore
def engine():  # noqa: N802 – keep name for imports
    return get_engine()


# Simple attribute-style access for `from app.core.database import engine`
class _EngineProxy:
    def __getattr__(self, name):
        return getattr(get_engine(), name)

    async def dispose(self):
        return await get_engine().dispose()


engine = _EngineProxy()  # type: ignore


class _SessionLocalProxy:
    def __call__(self, *args, **kwargs):
        return get_session_factory()(*args, **kwargs)


AsyncSessionLocal = _SessionLocalProxy()  # type: ignore


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables (dev only; use Alembic in production)."""
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
