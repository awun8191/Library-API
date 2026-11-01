"""Book resource data models and schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

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


NAME_MAX = 255
COURSE_CODE_MAX = 64


def normalize_course_code(value: str) -> str:
    """Store course codes in one form (upper case, no outer spaces)."""
    return value.strip().upper()


class BookUpdateRequest(BaseModel):
    """Schema for updating book details. Only the fields sent are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX)
    course_name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX)
    topic: str | None = Field(default=None, min_length=1, max_length=NAME_MAX)
    course_code: str | None = Field(default=None, min_length=1, max_length=COURSE_CODE_MAX)
    department_id: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("name", "course_name", "topic", "course_code", "department_id", mode="before")
    @classmethod
    def reject_null(cls, value):
        """Every book column is required, so an explicit null is invalid."""
        if value is None:
            raise ValueError("cannot be null")
        return value

    @field_validator("course_code")
    @classmethod
    def upper_course_code(cls, value: str | None) -> str | None:
        return normalize_course_code(value) if value is not None else value


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
