"""Authentication resource persistence contracts and queries."""
from typing import Optional, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from modules.users.data import UserCredentials, UserResponse
from schema.models import User


class AuthRepository(Protocol):
    """Account lookup and creation contract."""

    def get_credentials_by_email(self, email: str) -> Optional[UserCredentials]:
        """Fetch a user record with its password hash."""
        ...

    def create_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password_hash: str,
        department_id: Optional[int] = None,
    ) -> UserResponse:
        """Persist a new account and return its public fields."""
        ...


class SqlAlchemyAuthRepository:
    """SQLAlchemy implementation of the AuthRepository contract."""

    def __init__(self, session: Session):
        self.session = session

    def get_credentials_by_email(self, email: str) -> Optional[UserCredentials]:
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        user = self.session.execute(stmt).scalar_one_or_none()
        if not user:
            return None
        return UserCredentials.model_validate(user)

    def create_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password_hash: str,
        department_id: Optional[int] = None,
    ) -> UserResponse:
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=password_hash,
            role="user",
            is_active=True,
            department_id=department_id,
        )
        self.session.add(user)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        self.session.refresh(user)
        return UserResponse.model_validate(user)
