"""Department resource data models and schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DepartmentResponse(BaseModel):
    """Schema for department representation."""

    id: int
    name: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentCreateRequest(BaseModel):
    """Schema for creating a department."""

    name: str
