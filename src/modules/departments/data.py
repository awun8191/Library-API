"""Department resource data models and schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DepartmentResponse(BaseModel):
    """Schema for department representation."""
    id: int
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentCreateRequest(BaseModel):
    """Schema for creating a department."""
    name: str
