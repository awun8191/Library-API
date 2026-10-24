"""Authentication resource business rules and use cases."""
from typing import Optional

from sqlalchemy.exc import IntegrityError

from core.exceptions import (
    DepartmentNotFoundException,
    InvalidCredentialsException,
    UserAlreadyExistsException,
    UserForbiddenException,
)
from core.repository import PasswordHasher, TokenIssuer
from modules.auth.data import LoginRequest, SignupRequest, TokenResponse
from modules.auth.repository import AuthRepository
from modules.departments.repository import DepartmentRepository
from modules.users.data import UserResponse


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        hasher: PasswordHasher,
        token_issuer: TokenIssuer,
        dept_repo: Optional[DepartmentRepository] = None,
    ):
        self.repository = repository
        self.hasher = hasher
        self.token_issuer = token_issuer
        self.dept_repo = dept_repo

    def signup(self, payload: SignupRequest) -> UserResponse:
        email = str(payload.email).strip().lower()

        if self.repository.get_credentials_by_email(email) is not None:
            raise UserAlreadyExistsException("An account with this email already exists")

        if payload.department_id is not None and self.dept_repo is not None:
            if self.dept_repo.get_by_id(payload.department_id) is None:
                raise DepartmentNotFoundException()

        try:
            return self.repository.create_user(
                first_name=payload.first_name.strip(),
                last_name=payload.last_name.strip(),
                email=email,
                password_hash=self.hasher.hash(payload.password),
                department_id=payload.department_id,
            )
        except IntegrityError as exc:
            raise UserAlreadyExistsException("An account with this email already exists") from exc

    def login(self, payload: LoginRequest) -> TokenResponse:
        credentials = self.repository.get_credentials_by_email(str(payload.email))

        if credentials is None or not self.hasher.verify(payload.password, credentials.password_hash):
            raise InvalidCredentialsException()

        if not credentials.is_active:
            raise UserForbiddenException("This account is inactive")

        token, expires_in = self.token_issuer.issue(credentials.id)
        return TokenResponse(access_token=token, expires_in=expires_in)
