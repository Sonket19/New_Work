"""FastAPI application entry point for the AI Startup Analyst backend."""
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="AI Startup Analyst")
    app.include_router(router)
    return app


app = create_app()

