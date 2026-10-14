from fastapi import FastAPI
from core.config import AppSettings
from contextlib import asynccontextmanager
from core.exceptions import register_exception_handler
from modules.auth.router import get_auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

def initialize_app(settings: AppSettings):

    app = FastAPI(
        title=settings.api_name,
        description=settings.api_description,
        summary=settings.api_summary,
        version=settings.api_version,
        lifespan=lifespan,
    )

    register_exception_handler(app)
    app.include_router(router=get_auth_router(settings))

