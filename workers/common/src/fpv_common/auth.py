"""Supabase JWT handling.

M5 (dev): decode without verification; trust the `sub` claim as the user id.
M7 (hardening): verify with HS256 against SUPABASE_JWT_SECRET; expiry; audience.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import jwt


class AuthError(Exception):
    pass


@dataclass
class AuthedUser:
    user_id: UUID
    email: str | None


def decode_jwt(token: str, *, jwt_secret: str = "", verify: bool = False) -> AuthedUser:
    try:
        if verify and jwt_secret:
            # TODO(decision): tighten in M7 with audience/issuer checks.
            claims = jwt.decode(token, jwt_secret, algorithms=["HS256"],
                                options={"verify_aud": False})
        else:
            claims = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError as e:
        raise AuthError(f"invalid jwt: {e}") from e

    sub = claims.get("sub")
    if not sub:
        raise AuthError("jwt missing 'sub' claim")
    try:
        user_id = UUID(sub)
    except ValueError as e:
        raise AuthError(f"'sub' is not a uuid: {sub}") from e
    return AuthedUser(user_id=user_id, email=claims.get("email"))
