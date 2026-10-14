"""Authentication resource API routes."""
from fastapi import APIRouter

from core.config import AppSettings


def get_auth_router(settings: AppSettings) -> APIRouter:
    """Return the authentication router."""

    app = APIRouter()


    @app.post(f"/api/{settings.api_version}/auth/login", tags=["Login"])
    async def login():
        pass


    @app.post(f"/api/{settings.api_version}/auth/signup", tags=["SIGNUP"])
    async def signup():
        pass


    return app