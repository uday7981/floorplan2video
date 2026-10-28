"""Unified error shape per TRD: `{"error": {"code": "...", "message": "..."}}`.

Use raise ApiError(code=..., message=..., status_code=...). The exception
handler converts it to the right JSON + status code.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, *, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(_req: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code,
                            content=_body(exc.code, exc.message))
