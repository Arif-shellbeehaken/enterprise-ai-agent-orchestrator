"""API integration tests – auth endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepass1",
            "role": "Operator",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "Operator"
    assert "id" in data

    # Login
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "newuser@example.com", "password": "securepass1"},
    )
    assert res.status_code == 200, res.text
    token_data = res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["role"] == "Operator"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, admin_user):
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": admin_user.email,
            "password": "anotherpass1",
        },
    )
    assert res.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.email, "password": "wrongpassword"},
    )
    assert res.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body
