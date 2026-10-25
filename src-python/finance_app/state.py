"""Application state shared by all IPC commands."""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from finance_app.config import AppConfig, load_config, save_connection
from finance_app.database import Database
from finance_app.errors import AppError
from finance_app.schemas import SystemStatus

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    config: AppConfig
    db: Database
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _started_monotonic: float = field(default_factory=time.monotonic)

    @classmethod
    def create(cls) -> AppState:
        return cls(config=load_config(), db=Database())

    @property
    def uptime_seconds(self) -> float:
        return round(time.monotonic() - self._started_monotonic, 1)

    async def startup(self) -> None:
        logger.info(
            "Starting FinanceApp %s (python %s, config=%s, db=%s)",
            self.config.version,
            sys.version.split()[0],
            self.config.source,
            self.config.mongodb_db,
        )
        if not self.config.mongodb_uri:
            logger.warning(
                "No MongoDB URI configured. Use the database setup on the login screen, "
                "set FINANCE_MONGODB_URI, or use Settings → Database."
            )
            return
        try:
            await self.db.connect(self.config.mongodb_uri, self.config.mongodb_db)
        except AppError as exc:
            # A desktop app must still open so the user can fix the connection.
            logger.warning("Starting in offline mode: %s", exc.message)

    async def shutdown(self) -> None:
        await self.db.disconnect()

    async def reconfigure(self, uri: str, db_name: str) -> SystemStatus:
        """Test a new connection before persisting it, then swap it in."""

        candidate = Database()
        try:
            await candidate.connect(uri, db_name)
        except AppError:
            await candidate.disconnect()
            raise

        # Persist before swapping the live connection. If the config file
        # cannot be written, keep the old database active so the in-memory
        # state and the next startup agree.
        try:
            new_config = save_connection(self.config, uri, db_name)
        except Exception:
            await candidate.disconnect()
            raise

        old_db = self.db
        self.db = candidate
        self.config = new_config
        try:
            await old_db.disconnect()
        except Exception:  # noqa: BLE001 - closing the old pool is best-effort
            logger.warning("Could not close the previous MongoDB connection")
        return await self.status()

    async def status(self) -> SystemStatus:
        latency = await self.db.ping()
        connected = latency is not None
        return SystemStatus(
            app_version=self.config.version,
            python_version=sys.version.split()[0],
            db_connected=connected,
            db_latency_ms=latency,
            db_name=self.config.mongodb_db,
            db_uri_masked=self.config.masked_uri,
            config_source=self.config.source,
            data_dir=str(self.config.data_dir),
            last_error=self.db.last_error,
            offline=not connected,
        )
