"""MongoDB Atlas connection lifecycle (PyMongo async + Beanie)."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress
from typing import Any

from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from finance_app.config import redact_uri_passwords
from finance_app.errors import AppError
from finance_app.models import DOCUMENT_MODELS

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT_MS = 8_000
_RETRY_COOLDOWN_S = 3.0


class Database:
    """Small wrapper that keeps the app usable when Atlas is unreachable."""

    def __init__(self) -> None:
        self.client: AsyncMongoClient[Any] | None = None
        self.db: AsyncDatabase[Any] | None = None
        self.connected = False
        self.last_error: str | None = None
        self._last_attempt = 0.0
        self._lock = asyncio.Lock()

    async def connect(self, uri: str, db_name: str) -> None:
        async with self._lock:
            await self._connect_locked(uri, db_name)

    async def _connect_locked(self, uri: str, db_name: str) -> None:
        self._last_attempt = time.monotonic()
        await self._close_locked()

        logger.info("Connecting to MongoDB database %r", db_name)
        client: AsyncMongoClient[Any] | None = None
        try:
            client = AsyncMongoClient(
                uri,
                serverSelectionTimeoutMS=_CONNECT_TIMEOUT_MS,
                connectTimeoutMS=_CONNECT_TIMEOUT_MS,
                socketTimeoutMS=15_000,
                tz_aware=True,
                appname="FinanceApp",
            )
            await asyncio.wait_for(
                client.admin.command("ping"),
                timeout=_CONNECT_TIMEOUT_MS / 1000 + 2,
            )
            database = client[db_name]
            await init_beanie(database=database, document_models=DOCUMENT_MODELS)

            self.client = client
            self.db = database
            self.connected = True
            self.last_error = None
            logger.info("MongoDB connected")
        except Exception as exc:
            if client is not None:
                with suppress(Exception):
                    await client.close()
            self.connected = False
            self.client = None
            self.db = None
            self.last_error = redact_uri_passwords(f"{type(exc).__name__}: {exc}")[:400]
            logger.warning("MongoDB connection failed: %s", self.last_error)
            raise AppError(
                "DB_UNAVAILABLE",
                "Tidak dapat terhubung ke MongoDB. Periksa connection string dan "
                "whitelist IP Atlas Anda.",
                details={"error": type(exc).__name__},
            ) from exc

    async def ensure_connected(self) -> None:
        if self.connected:
            return
        elapsed = time.monotonic() - self._last_attempt
        if elapsed < _RETRY_COOLDOWN_S:
            raise AppError(
                "DB_UNAVAILABLE",
                "Database sedang tidak tersedia. Mencoba lagi…",
                details={"retry_after": round(_RETRY_COOLDOWN_S - elapsed, 1)},
            )
        raise AppError(
            "DB_UNAVAILABLE",
            "Database belum terhubung. Tekan Atur di halaman login atau buka "
            "Pengaturan → Database untuk mencoba lagi.",
        )

    async def ping(self) -> float | None:
        if not self.connected or self.client is None:
            return None
        started = time.perf_counter()
        try:
            await asyncio.wait_for(self.client.admin.command("ping"), timeout=2.5)
        except Exception as exc:  # noqa: BLE001
            self.connected = False
            self.last_error = redact_uri_passwords(f"{type(exc).__name__}: {exc}")[:400]
            logger.warning("MongoDB ping failed: %s", self.last_error)
            return None
        return round((time.perf_counter() - started) * 1000, 1)

    async def disconnect(self) -> None:
        async with self._lock:
            await self._close_locked()

    async def _close_locked(self) -> None:
        client = self.client
        self.client = None
        self.db = None
        self.connected = False
        if client is not None:
            try:
                await client.close()
            except Exception as exc:  # noqa: BLE001 - closing must not mask the real error
                logger.debug(
                    "Ignoring error while closing MongoDB client: %s",
                    redact_uri_passwords(f"{type(exc).__name__}: {exc}")[:400],
                )
