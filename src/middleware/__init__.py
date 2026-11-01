"""Middleware registration."""
from fastapi import FastAPI

from core.config import AppSettings
from middleware.cors import add_cors_middleware
from middleware.rate_limit import add_rate_limit_middleware


def register_middleware(app: FastAPI, settings: AppSettings) -> None:
    """Attach every application middleware.

    The last middleware added runs first. CORS is added last, so it stays
    outermost and its headers also reach a rate limited response.
    """
    add_rate_limit_middleware(app)
    add_cors_middleware(app, settings)
