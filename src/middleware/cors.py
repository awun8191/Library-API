"""Cross origin resource sharing middleware."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import AppSettings


def add_cors_middleware(app: FastAPI, settings: AppSettings) -> None:
    """Allow browser clients on the configured origins."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["WWW-Authenticate"],
    )
