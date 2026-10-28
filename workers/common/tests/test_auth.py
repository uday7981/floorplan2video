from __future__ import annotations

import jwt
import pytest
from uuid import UUID

from fpv_common.auth import AuthError, decode_jwt


def _make_jwt(claims: dict, secret: str = "test") -> str:
    return jwt.encode(claims, secret, algorithm="HS256")


def test_decode_without_verification_returns_user():
    user_uuid = "00000000-0000-0000-0000-000000000001"
    token = _make_jwt({"sub": user_uuid, "email": "a@b.com"})
    user = decode_jwt(token, verify=False)
    assert user.user_id == UUID(user_uuid)
    assert user.email == "a@b.com"


def test_decode_with_verification_requires_secret():
    user_uuid = "00000000-0000-0000-0000-000000000002"
    secret = "s3cret"
    token = _make_jwt({"sub": user_uuid}, secret=secret)
    user = decode_jwt(token, jwt_secret=secret, verify=True)
    assert user.user_id == UUID(user_uuid)


def test_decode_rejects_missing_sub():
    token = _make_jwt({"email": "a@b.com"})
    with pytest.raises(AuthError, match="sub"):
        decode_jwt(token)


def test_decode_rejects_malformed_sub():
    token = _make_jwt({"sub": "not-a-uuid"})
    with pytest.raises(AuthError, match="uuid"):
        decode_jwt(token)


def test_decode_rejects_garbage_token():
    with pytest.raises(AuthError, match="invalid"):
        decode_jwt("not.a.jwt")
