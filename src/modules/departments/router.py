"""Department resource API routes."""
from typing import List
from fastapi import APIRouter, Depends, status

from core.config import AppSettings
from dependencies import get_current_user
from modules.departments.data import DepartmentResponse
from modules.users.data import UserResponse


def get_departments_router(settings: AppSettings) -> APIRouter:
    """Return the departments router."""
    router = APIRouter()

    @router.get(
        f"/api/{settings.api_version}/departments",
        response_model=List[DepartmentResponse],
        status_code=status.HTTP_200_OK,
        tags=["Departments"],
        summary="List departments",
        responses={
            200: {"description": "List of departments fetched successfully"},
            401: {"description": "Unauthenticated"},
        },
    )
    async def list_departments(
        current_user: UserResponse = Depends(get_current_user),
    ):
        """List all departments available for filtering and categorizing course materials."""
        # Stub list of departments
        return [
            DepartmentResponse(id=1, name="Computer Science"),
            DepartmentResponse(id=2, name="Electrical Engineering"),
        ]

    return router
