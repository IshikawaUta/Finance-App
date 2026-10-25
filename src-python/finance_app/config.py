"""Runtime configuration.

MongoDB and timezone settings precedence (highest first):

1. ``config.json`` in the OS app-data directory (saved by the login setup
   dialog or Settings UI)
2. Environment variables (``.env`` in development, injected at build time in CI)
3. Built-in defaults

The MongoDB connection string is never logged or returned unmasked.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from platformdirs import user_data_dir

from finance_app.constants import APP_NAME, APP_VERSION

logger = logging.getLogger(__name__)

DEFAULT_DB_NAME = "finance_app"
DEFAULT_TIMEZONE = "Asia/Jakarta"
JWT_TTL_DAYS = 30

_URI_PASSWORD_RE = re.compile(r"(://[^:/?#@]*:)[^@/?#]+@")


@dataclass(frozen=True)
class AppConfig:
    mongodb_uri: str | None
    mongodb_db: str
    jwt_secret: str
    timezone: str
    log_level: str
    data_dir: Path
    config_path: Path
    source: str  # "file" | "env" | "missing"
    version: str = APP_VERSION

    @property
    def tz(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            logger.warning("Unknown timezone %r, falling back to UTC", self.timezone)
            return ZoneInfo("UTC")

    @property
    def masked_uri(self) -> str | None:
        return mask_uri(self.mongodb_uri)

    def with_connection(self, uri: str, db_name: str) -> AppConfig:
        return replace(
            self,
            mongodb_uri=uri,
            mongodb_db=db_name,
            source="file",
        )


def redact_uri_passwords(value: str) -> str:
    """Mask passwords embedded in URI-like strings, including error messages."""

    return _URI_PASSWORD_RE.sub(r"\1***@", value)


def mask_uri(uri: str | None) -> str | None:
    if not uri:
        return None
    return redact_uri_passwords(uri)


def _load_env_file() -> None:
    """Load `.env` from the repo root during development only."""

    candidates = (
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    )
    for candidate in candidates:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return


def _read_file_config(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if v is not None}


def _write_private(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    with suppress(OSError):
        # Windows ACLs are managed by the OS; chmod is best-effort.
        tmp.chmod(0o600)
    tmp.replace(path)


def _load_jwt_secret(data_dir: Path) -> str:
    env_secret = os.getenv("FINANCE_JWT_SECRET", "").strip()
    if len(env_secret) >= 32:
        return env_secret

    secret_path = data_dir / "jwt.key"
    try:
        existing = secret_path.read_text(encoding="utf-8").strip()
    except OSError:
        existing = ""
    if len(existing) >= 32:
        return existing

    generated = secrets.token_urlsafe(48)
    _write_private(secret_path, generated)
    logger.info("Generated a new JWT signing key at %s", secret_path)
    return generated


def _valid_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError:
        logger.warning("Unknown timezone %r; using %s", name, DEFAULT_TIMEZONE)
        return DEFAULT_TIMEZONE
    return name


def load_config() -> AppConfig:
    _load_env_file()

    data_dir = Path(user_data_dir(APP_NAME, appauthor=False))
    data_dir.mkdir(parents=True, exist_ok=True)
    config_path = data_dir / "config.json"
    file_config = _read_file_config(config_path)

    file_uri = file_config.get("mongodb_uri", "").strip()
    env_uri = os.getenv("FINANCE_MONGODB_URI", "").strip()
    uri = file_uri or env_uri or None
    source = "file" if file_uri else "env" if env_uri else "missing"

    db_name = (
        file_config.get("mongodb_db", "").strip()
        or os.getenv("FINANCE_MONGODB_DB", "").strip()
        or DEFAULT_DB_NAME
    )

    timezone_name = _valid_timezone(
        file_config.get("timezone", "").strip()
        or os.getenv("FINANCE_TIMEZONE", "").strip()
        or DEFAULT_TIMEZONE
    )

    return AppConfig(
        mongodb_uri=uri,
        mongodb_db=db_name,
        jwt_secret=_load_jwt_secret(data_dir),
        timezone=timezone_name,
        log_level=os.getenv("FINANCE_LOG_LEVEL", "INFO").upper(),
        data_dir=data_dir,
        config_path=config_path,
        source=source,
    )


def save_connection(config: AppConfig, uri: str, db_name: str) -> AppConfig:
    """Persist a user-provided connection string with owner-only permissions."""

    payload = json.dumps(
        {"mongodb_uri": uri, "mongodb_db": db_name, "timezone": config.timezone},
        indent=2,
    )
    _write_private(config.config_path, payload)
    logger.info("Saved MongoDB connection settings to %s", config.config_path)
    return config.with_connection(uri, db_name)
