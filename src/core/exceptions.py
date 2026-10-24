#  ------------------------    BASE EXCEPTION   --------------------------------
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):

    message: str = "An unexpected error occurred"
    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    headers: Optional[dict[str, str]] = None

    def __init__(
        self,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        if headers is not None:
            self.headers = headers
        super().__init__(self.message)

# =======================   FILE EXCEPTIONS -----------------------------------------

class FileUploadException(AppException):
    message: str = "File upload failed"
    status_code: int = 400
    code: str = "FILE_UPLOAD_FAILED"

class FileNotFoundException(AppException):
    message: str = "File not found in storage"
    status_code: int = 404
    code: str = "FILE_NOT_FOUND"

class FileTooLargeException(AppException):
    message: str = "File is too large"
    status_code: int = 413
    code: str = "FILE_TOO_LARGE"

class DuplicateFileException(AppException):
    message: str = "Duplicate file: this document has already been uploaded"
    status_code: int = 409
    code: str = "DUPLICATE_FILE"

# ------------------------   USER EXCEPTIONS -----------------------------------------

class UserAlreadyExistsException(AppException):
    message: str = "User already exists"
    status_code: int = 409
    code: str = "USER_ALREADY_EXISTS"

class UserNotFoundException(AppException):
    message: str = "User not found"
    status_code: int = 404
    code: str = "USER_NOT_FOUND"

class UserNotAuthorizedException(AppException):
    message: str = "User not authorized"
    status_code: int = 401
    code: str = "UNAUTHENTICATED"

    def __init__(self, message: Optional[str] = None, **kwargs):
        super().__init__(message=message, headers={"WWW-Authenticate": "Bearer"}, **kwargs)

class UserForbiddenException(AppException):
    message: str = "Forbidden: insufficient permissions"
    status_code: int = 403
    code: str = "FORBIDDEN"

class InvalidCredentialsException(AppException):
    message: str = "Invalid email or password"
    status_code: int = 401
    code: str = "INVALID_CREDENTIALS"

    def __init__(self, message: Optional[str] = None, **kwargs):
        super().__init__(message=message, headers={"WWW-Authenticate": "Bearer"}, **kwargs)

class UserAccountCreationException(AppException):
    message: str = "User account creation failed"
    status_code: int = 400
    code: str = "USER_CREATION_FAILED"

# ------------------------   BOOK & DEPARTMENT EXCEPTIONS ----------------------------

class BookNotFoundException(AppException):
    message: str = "Book not found"
    status_code: int = 404
    code: str = "BOOK_NOT_FOUND"

class DepartmentNotFoundException(AppException):
    message: str = "Department not found"
    status_code: int = 404
    code: str = "DEPARTMENT_NOT_FOUND"



def register_exception_handler(app: FastAPI):

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.message, "code": exc.code},
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        """Give framework errors (unknown route, wrong method) the same shape."""
        codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": str(exc.detail), "code": codes.get(exc.status_code, "HTTP_ERROR")},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        """Return 400 (not FastAPI's default 422) for invalid input, with field-level details."""
        errors = [
            {
                "field": ".".join(str(part) for part in err.get("loc", []) if part not in ("body", "query", "path")),
                "error": err.get("msg"),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid request data", "code": "INVALID_REQUEST", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        """Never leak stack traces to clients."""
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error", "code": "INTERNAL_ERROR"},
        )
