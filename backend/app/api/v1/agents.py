"""Agent CRUD & configuration management."""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.agent import Agent
from app.models.user import User

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: str = Field(min_length=1)
    model_name: str = "gemini-2.0-flash"
    requires_approval: bool = True
    approval_threshold_usd: Decimal = Decimal("100.00")


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_name: Optional[str] = None
    requires_approval: Optional[bool] = None
    approval_threshold_usd: Optional[Decimal] = None


class AgentOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    system_prompt: str
    model_name: str
    requires_approval: bool
    approval_threshold_usd: float
    created_at: str

    class Config:
        from_attributes = True


def _to_out(agent: Agent) -> AgentOut:
    return AgentOut(
        id=str(agent.id),
        tenant_id=str(agent.tenant_id),
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        model_name=agent.model_name,
        requires_approval=agent.requires_approval,
        approval_threshold_usd=float(agent.approval_threshold_usd),
        created_at=agent.created_at.isoformat() if agent.created_at else "",
    )


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Manager")),
):
    agent = Agent(
        id=uuid4(),
        tenant_id=current_user.tenant_id,
        name=payload.name,
        description=payload.description,
        system_prompt=payload.system_prompt,
        model_name=payload.model_name,
        requires_approval=payload.requires_approval,
        approval_threshold_usd=payload.approval_threshold_usd,
    )
    db.add(agent)
    await db.flush()
    return _to_out(agent)


@router.get("", response_model=List[AgentOut])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Agent).where(Agent.tenant_id == current_user.tenant_id).order_by(Agent.created_at.desc())
    )
    agents = result.scalars().all()
    return [_to_out(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_out(agent)


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: UUID,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Manager")),
):
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    await db.flush()
    return _to_out(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("Admin")),
):
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
