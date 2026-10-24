"""Department resource API routes."""
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.config import AppSettings
from dependencies import get_db
from modules.departments.data import DepartmentResponse
from modules.departments.repository import SqlAlchemyDepartmentRepository
from modules.departments.service import DepartmentService


def get_departments_router(settings: AppSettings) -> APIRouter:
    """Return the departments router."""
    router = APIRouter(prefix=settings.api_prefix)

    @router.get(
        "/departments",
        response_model=List[DepartmentResponse],
        status_code=status.HTTP_200_OK,
        tags=["Departments"],
        summary="List departments",
        responses={
            200: {"description": "List of departments fetched successfully"},
        },
    )
    def list_departments(
        db: Session = Depends(get_db),
    ):
        """List all departments available for filtering and categorizing course materials."""
        service = DepartmentService(SqlAlchemyDepartmentRepository(db))
        return service.list_departments()

    return router
