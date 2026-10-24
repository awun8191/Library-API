"""User resource data models and schemas."""
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    """Public user response schema - the only user fields ever returned."""
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: str = "user"
    is_active: bool = True
    department_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserCredentials(BaseModel):
    """Internal record with the password hash. Never returned by the API."""
    id: int
    email: EmailStr
    password_hash: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    """Schema for updating current user profile."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department_id: Optional[int] = None
