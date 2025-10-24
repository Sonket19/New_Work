"""ASGI entry point for deploying the FastAPI application."""
from app.main import app  # re-export for ASGI servers expecting `main:app`

__all__ = ["app"]
