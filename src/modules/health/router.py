"""Health resource API routes."""

from fastapi import APIRouter, Response, status

from core.config import AppSettings
from modules.health.data import HealthResponse
from modules.health.service import HealthService


def get_health_router(settings: AppSettings) -> APIRouter:
    """Return the health router. It sits at the root and needs no token."""
    router = APIRouter(tags=["Health"])
    service = HealthService(version=settings.api_version)

    @router.get(
        "/health",
        response_model=HealthResponse,
        status_code=status.HTTP_200_OK,
        summary="Report the health of the application",
        responses={
            200: {"description": "The application and the database are ready"},
            503: {"description": "The database is not reachable"},
        },
    )
    def health(response: Response):
        """Return the state of the application and its database."""
        result = service.check()
        if result.database != "ok":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return result

    return router
