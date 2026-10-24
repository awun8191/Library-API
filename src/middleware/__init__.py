"""Middleware registration."""
from fastapi import FastAPI

from core.config import AppSettings
from middleware.cors import add_cors_middleware


def register_middleware(app: FastAPI, settings: AppSettings) -> None:
    """Attach every application middleware."""
    add_cors_middleware(app, settings)
