"""Middleware registration."""
from fastapi import FastAPI

from core.config import AppSettings
from middleware.body_size import add_body_size_middleware
from middleware.cors import add_cors_middleware
from middleware.rate_limit import add_rate_limit_middleware
from middleware.request_id import add_request_id_middleware


def register_middleware(app: FastAPI, settings: AppSettings) -> None:
    """Attach every application middleware.

    The last middleware added runs first. CORS is added last, so it stays
    outermost. The request identifier comes next, so every response carries
    the header, including a 429 and a 413.
    """
    add_rate_limit_middleware(app)
    add_body_size_middleware(app)
    add_request_id_middleware(app)
    add_cors_middleware(app, settings)
