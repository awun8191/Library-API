"""Authentication request and response schemas."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    """Schema for account registration."""
    first_name: str = Field(min_length=1, max_length=100, pattern=r".*\S.*")
    last_name: str = Field(min_length=1, max_length=100, pattern=r".*\S.*")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    department_id: Optional[int] = Field(default=None, gt=0)


class LoginRequest(BaseModel):
    """Schema for account login."""
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Schema for auth token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
