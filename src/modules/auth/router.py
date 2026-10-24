"""Authentication resource API routes."""
from fastapi import APIRouter, Depends, status

from core.config import AppSettings
from dependencies import get_auth_service
from modules.auth.data import LoginRequest, SignupRequest, TokenResponse
from modules.auth.service import AuthService
from modules.users.data import UserResponse


def get_auth_router(settings: AppSettings) -> APIRouter:
    """Return the authentication router."""
    router = APIRouter(prefix=settings.api_prefix)

    @router.post(
        "/auth/signup",
        response_model=UserResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Auth"],
        summary="Create an account",
        responses={
            201: {"description": "Account created successfully"},
            400: {"description": "Invalid request data"},
            404: {"description": "Department not found"},
            409: {"description": "An account with this email already exists"},
        },
    )
    def signup(payload: SignupRequest, service: AuthService = Depends(get_auth_service)):
        """Create a new user account."""
        return service.signup(payload)

    @router.post(
        "/auth/login",
        response_model=TokenResponse,
        status_code=status.HTTP_200_OK,
        tags=["Auth"],
        summary="Get an auth token",
        responses={
            200: {"description": "Authentication successful"},
            401: {"description": "Invalid credentials"},
            403: {"description": "Account is inactive"},
        },
    )
    def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)):
        """Authenticate a user and return an access token."""
        return service.login(payload)

    return router
