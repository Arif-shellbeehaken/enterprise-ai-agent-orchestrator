"""
FastAPI entry point – Enterprise AI Agent Orchestrator (production-hardened).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.database import engine, init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.api.v1 import auth, agents, workflows, audit

setup_logging()
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s v%s [%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    try:
        await init_db()
        logger.info("Database tables ready")
    except Exception as exc:
        # Allow boot without Postgres for local demo / unit tests
        logger.warning(
            "DB init skipped / failed (expected if Postgres not running): %s", exc
        )
    yield
    logger.info("Shutting down")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(agents.router, prefix=settings.API_V1_PREFIX)
app.include_router(workflows.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit.router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health():
    """Liveness probe – process is up."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/ready")
async def readiness():
    """Readiness probe – dependencies (DB) reachable."""
    db_ok = False
    try:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as exc:
        logger.debug("Readiness DB check failed: %s", exc)

    status_code = "ok" if db_ok else "degraded"
    return {
        "status": status_code,
        "checks": {"database": "ok" if db_ok else "unavailable"},
    }


@app.get("/")
async def root():
    return {
        "message": "Enterprise AI Agent Orchestrator API",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }
