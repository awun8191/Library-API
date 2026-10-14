#  ------------------------    BASE EXCEPTION   --------------------------------
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):

    message: str = ""
    status_code: int = 500

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

# =======================   FILE EXCEPTIONS -----------------------------------------

class FileUploadException(AppException):
    message: str = "File upload failed"
    status_code: int = 400

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

class UserAccountCreationException(AppException):
    message: str = "User account creation failed"
    status_code: int = 400








def register_exception_handler(app: FastAPI):

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.message},
        )


