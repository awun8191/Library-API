"""Health resource data models and schemas."""

from typing import Literal

from pydantic import BaseModel

HealthState = Literal["ok", "error"]


class HealthResponse(BaseModel):
    """Schema for the health of the application."""

    status: HealthState
    database: HealthState
    version: str
