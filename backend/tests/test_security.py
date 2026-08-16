"""Unit tests for password hashing and JWT helpers."""

import pytest
from uuid import uuid4

from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from jose import jwt
from app.core.config import settings


@pytest.mark.unit
def test_password_hash_and_verify():
    plain = "SecureP@ssw0rd!"
    hashed = get_password_hash(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong", hashed) is False


@pytest.mark.unit
def test_create_access_token_payload():
    uid = uuid4()
    tid = uuid4()
    token = create_access_token(subject=uid, tenant_id=tid, role="Admin")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == str(uid)
    assert payload["tenant_id"] == str(tid)
    assert payload["role"] == "Admin"
    assert "exp" in payload
