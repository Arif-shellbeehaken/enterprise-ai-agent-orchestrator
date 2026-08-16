"""API integration tests – agent CRUD + RBAC."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_list_agents(client: AsyncClient, admin_user):
    headers = auth_header(admin_user)
    res = await client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "name": "Finance Agent",
            "system_prompt": "Handle financial ops carefully.",
            "requires_approval": True,
            "approval_threshold_usd": 50,
        },
    )
    assert res.status_code == 201, res.text
    agent = res.json()
    assert agent["name"] == "Finance Agent"
    assert agent["approval_threshold_usd"] == 50.0
    assert agent["tenant_id"] == str(admin_user.tenant_id)

    res = await client.get("/api/v1/agents", headers=headers)
    assert res.status_code == 200
    agents = res.json()
    assert any(a["id"] == agent["id"] for a in agents)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_operator_cannot_create_agent(client: AsyncClient, operator_user):
    headers = auth_header(operator_user)
    res = await client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "name": "Blocked",
            "system_prompt": "x",
        },
    )
    assert res.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient, admin_user, sample_agent):
    headers = auth_header(admin_user)
    res = await client.get(f"/api/v1/agents/{sample_agent.id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == sample_agent.name


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_agent(client: AsyncClient, admin_user, sample_agent):
    headers = auth_header(admin_user)
    res = await client.patch(
        f"/api/v1/agents/{sample_agent.id}",
        headers=headers,
        json={"name": "Renamed Agent", "approval_threshold_usd": 200},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Renamed Agent"
    assert body["approval_threshold_usd"] == 200.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unauthenticated_rejected(client: AsyncClient):
    res = await client.get("/api/v1/agents")
    assert res.status_code == 401
