"""Application dependency wiring shared across resource modules."""
from functools import lru_cache
from typing import Generator, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.exceptions import UserForbiddenException, UserNotAuthorizedException
from core.repository import PasswordHasher, TokenIssuer
from core.config import get_settings
from integrations.database import get_db_manager
from integrations.file_storage import FileStorage
from integrations.security import Argon2PasswordHasher, JwtTokenIssuer
from modules.auth.repository import SqlAlchemyAuthRepository
from modules.auth.service import AuthService
from modules.books.repository import SqlAlchemyBookRepository
from modules.books.service import BookService
from modules.departments.repository import SqlAlchemyDepartmentRepository
from modules.users.data import UserResponse
from modules.users.repository import SqlAlchemyUserRepository
from modules.users.service import UserService

security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session per request."""
    manager = get_db_manager()
    yield from manager.get_session()


@lru_cache()
def get_password_hasher() -> PasswordHasher:
    """Return the shared password hasher."""
    return Argon2PasswordHasher()


@lru_cache()
def get_token_issuer() -> TokenIssuer:
    """Return the shared access token issuer."""
    settings = get_settings()
    return JwtTokenIssuer(
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.access_token_expire_minutes,
    )


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dependency that instantiates the authentication service."""
    return AuthService(
        repository=SqlAlchemyAuthRepository(db),
        hasher=get_password_hasher(),
        token_issuer=get_token_issuer(),
        dept_repo=SqlAlchemyDepartmentRepository(db),
    )


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency that instantiates the user service."""
    return UserService(
        user_repo=SqlAlchemyUserRepository(db),
        dept_repo=SqlAlchemyDepartmentRepository(db),
    )


@lru_cache()
def get_file_storage() -> FileStorage:
    """Return the shared local file storage."""
    return FileStorage()


def get_book_service(db: Session = Depends(get_db)) -> BookService:
    """Dependency that instantiates the book service."""
    return BookService(
        book_repo=SqlAlchemyBookRepository(db),
        file_storage=get_file_storage(),
        dept_repo=SqlAlchemyDepartmentRepository(db),
        max_upload_bytes=get_settings().max_upload_size_bytes,
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
    token_issuer: TokenIssuer = Depends(get_token_issuer),
) -> UserResponse:
    """Dependency that resolves the authenticated user from the bearer token."""
    if credentials is None or not credentials.credentials:
        raise UserNotAuthorizedException("Authentication token is missing")

    user_id = token_issuer.decode_user_id(credentials.credentials)
    if user_id is None:
        raise UserNotAuthorizedException("Invalid or expired authentication token")

    user = SqlAlchemyUserRepository(db).get_by_id(user_id)
    if user is None:
        raise UserNotAuthorizedException("Invalid or expired authentication token")
    if not user.is_active:
        raise UserForbiddenException("This account is inactive")
    return user


def require_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Dependency ensuring the user has an admin role."""
    if current_user.role != "admin":
        raise UserForbiddenException("Admin access required")
    return current_user
