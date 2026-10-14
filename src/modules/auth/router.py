"""Authentication resource API routes."""
from fastapi import APIRouter, status

from core.config import AppSettings
from modules.auth.data import LoginRequest, SignupRequest, TokenResponse
from modules.users.data import UserResponse


def get_auth_router(settings: AppSettings) -> APIRouter:
    """Return the authentication router."""
    router = APIRouter()

    @router.post(
        f"/api/{settings.api_version}/auth/signup",
        response_model=UserResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Auth"],
        summary="Create an account",
        responses={
            201: {"description": "Account created successfully"},
            400: {"description": "Bad request or user already exists"},
        },
    )
    async def signup(payload: SignupRequest):
        """Create a new user account."""
        # Stub implementation pending service logic wiring
        return UserResponse(
            id=1,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            role="user",
            is_active=True,
            department_id=payload.department_id,
        )

    @router.post(
        f"/api/{settings.api_version}/auth/login",
        response_model=TokenResponse,
        status_code=status.HTTP_200_OK,
        tags=["Auth"],
        summary="Get an auth token",
        responses={
            200: {"description": "Authentication successful"},
            401: {"description": "Invalid credentials"},
        },
    )
    async def login(payload: LoginRequest):
        """Authenticate user and return an access token."""
        # Stub implementation pending service logic wiring
        return TokenResponse(
            access_token="dev_placeholder_access_token",
            token_type="bearer",
        )

    return router