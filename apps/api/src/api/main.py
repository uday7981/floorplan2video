"""FastAPI entry. `fpv-api` or `uvicorn api.main:app --reload`."""
from __future__ import annotations

import os

from fastapi import FastAPI

from . import errors
from .routers import exports, files, generations, plans, projects, shots


def create_app() -> FastAPI:
    app = FastAPI(
        title="Floor Plan to Video API",
        version="0.1.0",
        openapi_url="/v1/openapi.json",
        docs_url="/v1/docs",
    )

    @app.get("/healthz")
    def health():
        return {"ok": True}

    v1 = FastAPI()  # we mount sub-routers with their own paths; prefix via APIRouter

    app.include_router(projects.router,     prefix="/v1")
    app.include_router(plans.router,        prefix="/v1")
    app.include_router(shots.router,        prefix="/v1")
    app.include_router(generations.router,  prefix="/v1")
    app.include_router(exports.router,      prefix="/v1")
    app.include_router(files.router,        prefix="/v1")

    errors.register(app)
    return app


app = create_app()


def run() -> None:
    import uvicorn
    uvicorn.run("api.main:app",
                host=os.environ.get("API_HOST", "0.0.0.0"),
                port=int(os.environ.get("API_PORT", "8000")),
                reload=False)
