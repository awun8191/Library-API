"""User resource business rules and use cases."""
from typing import Optional

from core.exceptions import DepartmentNotFoundException, UserNotFoundException
from modules.departments.repository import DepartmentRepository
from modules.users.data import UserResponse, UserUpdateRequest
from modules.users.repository import UserRepository


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        dept_repo: Optional[DepartmentRepository] = None,
    ):
        self.user_repo = user_repo
        self.dept_repo = dept_repo

    def get_user_profile(self, user_id: int) -> UserResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        return user

    def update_user_profile(self, user_id: int, payload: UserUpdateRequest) -> UserResponse:
        if payload.department_id is not None and self.dept_repo is not None:
            dept = self.dept_repo.get_by_id(payload.department_id)
            if not dept:
                raise DepartmentNotFoundException()

        updated_user = self.user_repo.update_user(user_id, payload)
        if not updated_user:
            raise UserNotFoundException()
        return updated_user
