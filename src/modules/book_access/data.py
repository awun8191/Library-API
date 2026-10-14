"""Book-access history data models and schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class BookAccessResponse(BaseModel):
    """Schema for book access record."""
    id: int
    user_id: int
    book_id: int
    accessed_at: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BookAccessItemResponse(BaseModel):
    """Schema for book access entry in history."""
    id: int
    book_id: int
    book_name: Optional[str] = None
    course_code: Optional[str] = None
    accessed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookAccessHistoryResponse(BaseModel):
    """Schema for paginated access history response."""
    items: List[BookAccessItemResponse]
    next_cursor: Optional[int] = None
    has_more: bool = False