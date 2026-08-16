"""API integration tests – workflow run + HITL approve/reject."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_read_only_completes(
    client: AsyncClient, admin_user, sample_agent
):
    headers = auth_header(admin_user)
    res = await client.post(
        "/api/v1/workflows/run",
        headers=headers,
        json={
            "agent_id": str(sample_agent.id),
            "query": "What is the status of the open opportunities?",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] in ("COMPLETED", "APPROVED", "SANITIZED", "TOOL_DECISION", "PLANNING") or not body["needs_approval"]
    # Read-only should not require approval
    if body.get("tool_action") != "external_write":
        assert body["needs_approval"] is False or body["status"] == "COMPLETED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_high_value_payout_needs_approval(
    client: AsyncClient, admin_user, sample_agent
):
    headers = auth_header(admin_user)
    res = await client.post(
        "/api/v1/workflows/run",
        headers=headers,
        json={
            "agent_id": str(sample_agent.id),
            "query": "Process a $250 payout to vendor ACME Corp",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["needs_approval"] is True
    assert body["status"] == "PENDING_APPROVAL"
    assert body["thread_id"]
    assert body["interrupt_reason"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_approve_pending_workflow(
    client: AsyncClient, admin_user, sample_agent
):
    headers = auth_header(admin_user)
    # Trigger HITL
    res = await client.post(
        "/api/v1/workflows/run",
        headers=headers,
        json={
            "agent_id": str(sample_agent.id),
            "query": "Execute payment transfer of $500 to supplier",
        },
    )
    assert res.status_code == 200
    thread_id = res.json()["thread_id"]
    assert res.json()["needs_approval"] is True

    # List pending
    res = await client.get("/api/v1/workflows/pending", headers=headers)
    assert res.status_code == 200
    pending = res.json()
    assert any(p["thread_id"] == thread_id for p in pending)

    # Approve
    res = await client.post(
        "/api/v1/workflows/approve",
        headers=headers,
        json={
            "thread_id": thread_id,
            "decision": "approve",
            "comment": "Verified vendor bank details",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] in ("APPROVED", "COMPLETED")
    assert body["needs_approval"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reject_pending_workflow(
    client: AsyncClient, admin_user, sample_agent
):
    headers = auth_header(admin_user)
    res = await client.post(
        "/api/v1/workflows/run",
        headers=headers,
        json={
            "agent_id": str(sample_agent.id),
            "query": "Process a $999 payout now",
        },
    )
    thread_id = res.json()["thread_id"]

    res = await client.post(
        "/api/v1/workflows/approve",
        headers=headers,
        json={
            "thread_id": thread_id,
            "decision": "reject",
            "comment": "Amount exceeds policy",
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_unknown_agent_404(client: AsyncClient, admin_user):
    headers = auth_header(admin_user)
    from uuid import uuid4

    res = await client.post(
        "/api/v1/workflows/run",
        headers=headers,
        json={"agent_id": str(uuid4()), "query": "test"},
    )
    assert res.status_code == 404
