#  ------------------------    BASE EXCEPTION   --------------------------------
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppException(Exception):

    message: str = "An unexpected error occurred"
    status_code: int = 500

    def __init__(
        self,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)

# =======================   FILE EXCEPTIONS -----------------------------------------

class FileUploadException(AppException):
    message: str = "File upload failed"
    status_code: int = 400

class DuplicateFileException(AppException):
    message: str = "Duplicate file: this document has already been uploaded"
    status_code: int = 409

# ------------------------   USER EXCEPTIONS -----------------------------------------

class UserAlreadyExistsException(AppException):
    message: str = "User already exists"
    status_code: int = 400

class UserNotFoundException(AppException):
    message: str = "User not found"
    status_code: int = 404

class UserNotAuthorizedException(AppException):
    message: str = "User not authorized"
    status_code: int = 401

class UserForbiddenException(AppException):
    message: str = "Forbidden: insufficient permissions"
    status_code: int = 403

class InvalidCredentialsException(AppException):
    message: str = "Invalid email or password"
    status_code: int = 401

class UserAccountCreationException(AppException):
    message: str = "User account creation failed"
    status_code: int = 400

# ------------------------   BOOK & DEPARTMENT EXCEPTIONS ----------------------------

class BookNotFoundException(AppException):
    message: str = "Book not found"
    status_code: int = 404

class DepartmentNotFoundException(AppException):
    message: str = "Department not found"
    status_code: int = 404








def register_exception_handler(app: FastAPI):

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.message},
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
            content={"message": "Invalid request data", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        """Never leak stack traces to clients."""
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error"},
        )
