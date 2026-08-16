"""
Workflow execution triggers and Human-in-the-Loop approval endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.engine.graph_builder import get_agent_graph, AgentState
from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])

# In-memory thread store for demo (replace with Postgres checkpointer in prod)
_thread_store: Dict[str, Dict[str, Any]] = {}


class WorkflowRunRequest(BaseModel):
    agent_id: UUID
    query: str = Field(min_length=1)
    thread_id: Optional[str] = None  # resume existing run


class WorkflowRunResponse(BaseModel):
    thread_id: str
    status: str
    interrupt_reason: Optional[str] = None
    execution_result: Optional[str] = None
    audit_id: Optional[str] = None
    needs_approval: bool = False


class ApprovalDecision(BaseModel):
    thread_id: str
    decision: str = Field(pattern="^(approve|reject)$")
    comment: Optional[str] = None


class PendingApprovalOut(BaseModel):
    thread_id: str
    agent_id: str
    query: str
    sanitized_query: Optional[str]
    estimated_cost_usd: float
    interrupt_reason: Optional[str]
    status: str
    created_at: Optional[str] = None


@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(
    payload: WorkflowRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Load agent (tenant isolation)
    result = await db.execute(
        select(Agent).where(
            Agent.id == payload.agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    thread_id = payload.thread_id or str(uuid4())
    graph = get_agent_graph()

    initial_state: AgentState = {
        "query": payload.query,
        "tenant_id": str(current_user.tenant_id),
        "agent_id": str(agent.id),
        "user_id": str(current_user.id),
        "agent_system_prompt": agent.system_prompt,
        "approval_threshold_usd": float(agent.approval_threshold_usd),
        "requires_approval": agent.requires_approval,
        "approval_status": "pending",
        "status": "STARTED",
    }

    config = {"configurable": {"thread_id": thread_id}}
    final_state: Dict[str, Any] = {}

    try:
        # Stream / invoke until interrupt or completion
        async for event in graph.astream(initial_state, config=config):
            if not isinstance(event, dict):
                continue
            for node_name, node_state in event.items():
                if isinstance(node_state, dict):
                    final_state.update(node_state)
                    logger.debug("Node %s → %s", node_name, node_state.get("status"))
                elif isinstance(node_state, tuple):
                    # Some LangGraph versions emit (namespace, state) tuples
                    for part in node_state:
                        if isinstance(part, dict):
                            final_state.update(part)
    except Exception as exc:
        logger.exception("Graph execution failed")
        raise HTTPException(status_code=500, detail=str(exc))

    status_val = final_state.get("status", "UNKNOWN")
    needs_approval = status_val == "PENDING_APPROVAL"

    # Persist audit log
    audit = AuditLog(
        id=uuid4(),
        tenant_id=current_user.tenant_id,
        agent_id=agent.id,
        action_taken=final_state.get("tool_action") or "plan",
        sanitized_input=final_state.get("sanitized_query"),
        execution_result=final_state.get("execution_result"),
        status=status_val,
        reviewed_by=None,
    )
    db.add(audit)
    await db.flush()

    # Keep state for later resume
    _thread_store[thread_id] = {
        **final_state,
        "audit_id": str(audit.id),
        "agent_id": str(agent.id),
        "tenant_id": str(current_user.tenant_id),
    }

    return WorkflowRunResponse(
        thread_id=thread_id,
        status=status_val,
        interrupt_reason=final_state.get("interrupt_reason"),
        execution_result=final_state.get("execution_result"),
        audit_id=str(audit.id),
        needs_approval=needs_approval,
    )


@router.post("/approve", response_model=WorkflowRunResponse)
async def decide_approval(
    payload: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Manager", "Operator")),
):
    stored = _thread_store.get(payload.thread_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Thread not found or already completed")

    if stored.get("tenant_id") != str(current_user.tenant_id):
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    decision = payload.decision.lower()
    new_status = "APPROVED" if decision == "approve" else "REJECTED"

    # Update audit log
    audit_id = stored.get("audit_id")
    if audit_id:
        result = await db.execute(
            select(AuditLog).where(AuditLog.id == UUID(audit_id))
        )
        audit = result.scalar_one_or_none()
        if audit:
            audit.status = new_status
            audit.reviewed_by = current_user.id
            if decision == "approve":
                # Simulate continued execution
                audit.execution_result = (
                    f"Human-approved execution completed. Comment: {payload.comment or 'n/a'}"
                )
                new_status = "COMPLETED"
                audit.status = "COMPLETED"
            else:
                audit.execution_result = f"Rejected by {current_user.email}: {payload.comment or ''}"

    # Clean up thread
    _thread_store.pop(payload.thread_id, None)

    return WorkflowRunResponse(
        thread_id=payload.thread_id,
        status=new_status,
        execution_result=audit.execution_result if audit_id and audit else None,
        audit_id=audit_id,
        needs_approval=False,
    )


@router.get("/pending", response_model=List[PendingApprovalOut])
async def list_pending_approvals(
    current_user: User = Depends(get_current_user),
):
    pending = []
    for tid, state in _thread_store.items():
        if (
            state.get("status") == "PENDING_APPROVAL"
            and state.get("tenant_id") == str(current_user.tenant_id)
        ):
            pending.append(
                PendingApprovalOut(
                    thread_id=tid,
                    agent_id=state.get("agent_id", ""),
                    query=state.get("query", ""),
                    sanitized_query=state.get("sanitized_query"),
                    estimated_cost_usd=float(state.get("estimated_cost_usd") or 0),
                    interrupt_reason=state.get("interrupt_reason"),
                    status=state.get("status", ""),
                )
            )
    return pending
