"""User resource data models and schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    """Public user response schema - the only user fields ever returned."""

    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: str = "user"
    is_active: bool = True
    department_id: int | None = None

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

    first_name: str | None = None
    last_name: str | None = None
    department_id: int | None = None
