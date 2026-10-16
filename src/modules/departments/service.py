"""Department resource business rules and use cases."""
from typing import List

from core.exceptions import DepartmentNotFoundException
from modules.departments.data import DepartmentResponse
from modules.departments.repository import DepartmentRepository


class DepartmentService:
    def __init__(self, repository: DepartmentRepository):
        self.repository = repository

    def list_departments(self) -> List[DepartmentResponse]:
        return self.repository.list_departments()

    def get_department(self, department_id: int) -> DepartmentResponse:
        dept = self.repository.get_by_id(department_id)
        if not dept:
            raise DepartmentNotFoundException()
        return dept
