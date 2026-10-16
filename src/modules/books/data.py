"""Book resource data models and schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class BookResponse(BaseModel):
    """Schema for book details."""
    id: int
    name: str
    course_name: str
    topic: str
    course_code: str
    department_id: int
    file_url: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BookUpdateRequest(BaseModel):
    """Schema for updating book details."""
    name: Optional[str] = None
    course_name: Optional[str] = None
    topic: Optional[str] = None
    course_code: Optional[str] = None
    department_id: Optional[int] = None


class BookListResponse(BaseModel):
    """Schema for paginated list of books."""
    items: List[BookResponse]
    next_cursor: Optional[int] = None
    has_more: bool = False


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
