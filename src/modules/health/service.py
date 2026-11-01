"""Health resource business rules."""
import logging

from sqlalchemy import text

from integrations.database import get_db_manager
from modules.health.data import HealthResponse

logger = logging.getLogger(__name__)


class HealthService:
    """Report whether the application can reach its database."""

    def __init__(self, version: str):
        self.version = version

    def check(self) -> HealthResponse:
        """Run a small query. Report an error instead of raising."""
        database = "ok"
        try:
            session_factory = get_db_manager().session_factory
            with session_factory() as session:
                session.execute(text("SELECT 1"))
        except Exception as exc:
            # A health check must answer. The caller wants the state, not a raise.
            logger.warning("The database health check failed: %s", exc)
            database = "error"

        return HealthResponse(status=database, database=database, version=self.version)
