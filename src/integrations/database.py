from functools import lru_cache
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import AppSettings, get_settings


class DatabaseManager:
    """Encapsulates database engine creation, session factory, and connection lifecycle."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    def get_session(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session

    def close(self) -> None:
        self.engine.dispose()


_db_manager: DatabaseManager | None = None


def get_db_manager(database_url: str | None = None) -> DatabaseManager:
    global _db_manager
    if _db_manager is None or database_url is not None:
        url = database_url or get_settings().database_url
        _db_manager = DatabaseManager(url)
    return _db_manager
