"""User resource data models and schemas."""
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Role = Literal["admin", "user"]


class UserResponse(BaseModel):
    """Public user response schema - the only user fields ever returned."""
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: Role = "user"
    is_active: bool = True
    department_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserCredentials(BaseModel):
    """Internal record with the password hash. Never returned by the API."""
    id: int
    email: EmailStr
    password_hash: str
    role: Role
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    """Schema for updating the current user's profile. Only the fields sent are changed.

    ``department_id`` may be sent as null to leave a department.
    """
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    department_id: Optional[int] = Field(default=None, gt=0)

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def reject_null(cls, value):
        """Names are required columns, so an explicit null is invalid."""
        if value is None:
            raise ValueError("cannot be null")
        return value
