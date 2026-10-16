from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.config import AppSettings
from core.exceptions import register_exception_handler
from integrations.database import get_db_manager
from modules.auth.router import get_auth_router
from modules.books.router import get_books_router
from modules.departments.router import get_departments_router
from modules.users.router import get_users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    get_db_manager().close()


def initialize_app(settings: AppSettings) -> FastAPI:
    """Initialize and configure the FastAPI application."""
    app = FastAPI(
        title=settings.api_name,
        description=settings.api_description,
        summary=settings.api_summary,
        version=settings.api_version,
        lifespan=lifespan,
    )

    register_exception_handler(app)

    # Register resource routers
    app.include_router(router=get_auth_router(settings))
    app.include_router(router=get_users_router(settings))
    app.include_router(router=get_books_router(settings))
    app.include_router(router=get_departments_router(settings))

    return app


if __name__ == "__main__":
    app = initialize_app(settings=AppSettings())