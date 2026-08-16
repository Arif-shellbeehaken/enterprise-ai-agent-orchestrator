"""Governance & execution log query endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogOut(BaseModel):
    id: str
    tenant_id: str
    agent_id: Optional[str]
    action_taken: str
    sanitized_input: Optional[str]
    execution_result: Optional[str]
    status: str
    reviewed_by: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.get("/logs", response_model=List[AuditLogOut])
async def list_audit_logs(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == current_user.tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if status_filter:
        stmt = stmt.where(AuditLog.status == status_filter)

    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        AuditLogOut(
            id=str(log.id),
            tenant_id=str(log.tenant_id),
            agent_id=str(log.agent_id) if log.agent_id else None,
            action_taken=log.action_taken,
            sanitized_input=log.sanitized_input,
            execution_result=log.execution_result,
            status=log.status,
            reviewed_by=str(log.reviewed_by) if log.reviewed_by else None,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]


@router.get("/logs/{log_id}", response_model=AuditLogOut)
async def get_audit_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Manager")),
):
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.id == log_id,
            AuditLog.tenant_id == current_user.tenant_id,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit log not found")
    return AuditLogOut(
        id=str(log.id),
        tenant_id=str(log.tenant_id),
        agent_id=str(log.agent_id) if log.agent_id else None,
        action_taken=log.action_taken,
        sanitized_input=log.sanitized_input,
        execution_result=log.execution_result,
        status=log.status,
        reviewed_by=str(log.reviewed_by) if log.reviewed_by else None,
        created_at=log.created_at.isoformat() if log.created_at else "",
    )
