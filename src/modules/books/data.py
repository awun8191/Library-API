"""Book resource data models and schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from core.config import get_settings


def book_file_url(book_id: int) -> str:
    """Return the authenticated download path of a book."""
    return f"{get_settings().api_prefix}/books/{book_id}/file"


class BookResponse(BaseModel):
    """Schema for book details."""

    id: int
    name: str
    course_name: str
    topic: str
    course_code: str
    department_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def file_url(self) -> str:
        """Download path of the stored PDF."""
        return book_file_url(self.id)


class BookUpdateRequest(BaseModel):
    """Schema for updating book details."""

    name: str | None = None
    course_name: str | None = None
    topic: str | None = None
    course_code: str | None = None
    department_id: int | None = None


class BookListResponse(BaseModel):
    """Schema for paginated list of books."""

    items: list[BookResponse]
    next_cursor: int | None = None
    has_more: bool = False


class BookAccessResponse(BaseModel):
    """Schema for book access record."""

    id: int
    user_id: int
    book_id: int
    accessed_at: datetime
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BookAccessItemResponse(BaseModel):
    """Schema for book access entry in history."""

    id: int
    book_id: int
    book_name: str | None = None
    course_code: str | None = None
    accessed_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def file_url(self) -> str:
        """Download path of the stored PDF."""
        return book_file_url(self.book_id)


class BookAccessHistoryResponse(BaseModel):
    """Schema for paginated access history response."""

    items: list[BookAccessItemResponse]
    next_cursor: int | None = None
    has_more: bool = False
