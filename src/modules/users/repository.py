"""User resource persistence contracts and queries."""
from typing import Optional, Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.users.data import UserResponse, UserUpdateRequest
from schema.models import User


@runtime_checkable
class UserRepository(Protocol):
    def get_by_id(self, user_id: int) -> Optional[UserResponse]:
        """Fetch user by ID."""
        ...

    def update_user(self, user_id: int, payload: UserUpdateRequest) -> Optional[UserResponse]:
        """Update user profile fields."""
        ...


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[UserResponse]:
        stmt = select(User).where(User.id == user_id)
        user = self.session.execute(stmt).scalar_one_or_none()
        if not user:
            return None
        return UserResponse.model_validate(user)

    def update_user(self, user_id: int, payload: UserUpdateRequest) -> Optional[UserResponse]:
        stmt = select(User).where(User.id == user_id)
        user = self.session.execute(stmt).scalar_one_or_none()
        if not user:
            return None

        if payload.first_name is not None:
            user.first_name = payload.first_name
        if payload.last_name is not None:
            user.last_name = payload.last_name
        if payload.department_id is not None:
            user.department_id = payload.department_id

        self.session.commit()
        self.session.refresh(user)
        return UserResponse.model_validate(user)