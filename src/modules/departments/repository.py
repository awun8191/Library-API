"""Department resource persistence contracts and queries."""
from typing import List, Optional, Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.departments.data import DepartmentResponse
from schema.models import Department


@runtime_checkable
class DepartmentRepository(Protocol):
    def list_departments(self) -> List[DepartmentResponse]:
        """List all departments."""
        ...

    def get_by_id(self, department_id: int) -> Optional[DepartmentResponse]:
        """Fetch department by ID."""
        ...


class SqlAlchemyDepartmentRepository(DepartmentRepository):
    def __init__(self, session: Session):
        self.session = session

    def list_departments(self) -> List[DepartmentResponse]:
        stmt = select(Department).order_by(Department.name.asc())
        rows = self.session.execute(stmt).scalars().all()
        return [DepartmentResponse.model_validate(row) for row in rows]

    def get_by_id(self, department_id: int) -> Optional[DepartmentResponse]:
        stmt = select(Department).where(Department.id == department_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        if not row:
            return None
        return DepartmentResponse.model_validate(row)