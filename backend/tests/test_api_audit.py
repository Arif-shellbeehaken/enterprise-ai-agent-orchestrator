"""API integration tests – audit log queries."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_audit_logs_after_run(
    client: AsyncClient, admin_user, sample_agent
):
    headers = auth_header(admin_user)
    # Generate an audit row via workflow
    await client.post(
        "/api/v1/workflows/run",
        headers=headers,
        json={
            "agent_id": str(sample_agent.id),
            "query": "List open tickets",
        },
    )

    res = await client.get("/api/v1/audit/logs", headers=headers)
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1
    log = logs[0]
    assert "id" in log
    assert "status" in log
    assert "action_taken" in log
    assert log["tenant_id"] == str(admin_user.tenant_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_status_filter(
    client: AsyncClient, admin_user, sample_agent
):
    headers = auth_header(admin_user)
    await client.post(
        "/api/v1/workflows/run",
        headers=headers,
        json={
            "agent_id": str(sample_agent.id),
            "query": "Process a $300 payout",
        },
    )

    res = await client.get(
        "/api/v1/audit/logs?status=PENDING_APPROVAL", headers=headers
    )
    assert res.status_code == 200
    for log in res.json():
        assert log["status"] == "PENDING_APPROVAL"
