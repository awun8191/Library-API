from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.config import AppSettings, get_settings
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
        docs_url= "/docs" if settings.environment == "development" else None,
        redoc_url= "/redoc" if settings.environment == "development" else None,
    )

    register_exception_handler(app)

    # Mount static files to serve uploaded PDFs
    storage_dir = Path(__file__).resolve().parent.parent / "Storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/books", StaticFiles(directory=str(storage_dir)), name="static_books")

    # Register resource routers
    app.include_router(router=get_auth_router(settings))
    app.include_router(router=get_users_router(settings))
    app.include_router(router=get_books_router(settings))
    app.include_router(router=get_departments_router(settings))

    return app


app = initialize_app(settings=get_settings())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)