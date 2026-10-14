"""Authentication request and response schemas."""
from typing import Optional
from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    """Schema for account registration."""
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    department_id: Optional[int] = None


class LoginRequest(BaseModel):
    """Schema for account login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for auth token response."""
    access_token: str
    token_type: str = "bearer"
