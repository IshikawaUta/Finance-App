"""Structured error handling for the IPC boundary.

PyTauri transports errors as rejected promises whose value is a string.  We
standardise that string as JSON so the TypeScript client can display a useful
message and branch on a stable error code::

    {"code": "DB_UNAVAILABLE", "message": "…", "details": {"retry_after": 5}}

PyTauri is imported lazily so that domain modules (money, periods, services)
remain importable in unit tests without the compiled Rust extension.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, NoReturn

from pydantic import ValidationError
from pymongo.errors import PyMongoError

from finance_app.config import redact_uri_passwords

if TYPE_CHECKING:
    from pytauri.ipc import InvokeException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Expected, user-facing error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": redact_uri_passwords(self.message),
            "details": self.details,
        }

    def to_invoke(self) -> InvokeException:
        from pytauri.ipc import InvokeException

        return InvokeException(json.dumps(self.to_payload(), ensure_ascii=False))


def fail(code: str, message: str, **details: Any) -> NoReturn:
    """Raise an :class:`AppError` (helper for guard clauses)."""
    raise AppError(code, message, details=details or None)


@contextmanager
def api_errors() -> Iterator[None]:
    """Translate domain/database/unexpected errors into IPC rejections."""

    from pytauri.ipc import InvokeException

    try:
        yield
    except InvokeException:
        # Already serialized by a nested boundary.
        raise
    except AppError as exc:
        logger.warning("api error [%s]: %s", exc.code, redact_uri_passwords(exc.message))
        raise exc.to_invoke() from None
    except ValidationError as exc:
        # Never echo request input or validator context: a failed URI
        # validation would otherwise expose the connection string password in
        # both the IPC response and the application log.
        safe_errors = exc.errors(
            include_url=False,
            include_input=False,
            include_context=False,
        )
        logger.info(
            "validation error: %s",
            [{"loc": error.get("loc"), "type": error.get("type")} for error in safe_errors],
        )
        raise InvokeException(
            json.dumps(
                {
                    "code": "VALIDATION_ERROR",
                    "message": "Data yang dikirim tidak valid.",
                    "details": {"errors": safe_errors},
                },
                ensure_ascii=False,
                default=str,
            )
        ) from None
    except PyMongoError as exc:
        logger.warning(
            "database error: %s",
            redact_uri_passwords(f"{type(exc).__name__}: {exc}"),
        )
        raise InvokeException(
            json.dumps(
                {
                    "code": "DB_UNAVAILABLE",
                    "message": (
                        "Tidak dapat terhubung ke database. Periksa koneksi internet "
                        "dan pengaturan MongoDB di halaman login atau Pengaturan."
                    ),
                    "details": {"error": type(exc).__name__},
                },
                ensure_ascii=False,
            )
        ) from None
    except Exception as exc:  # noqa: BLE001 - IPC boundary must never leak a raw exception
        logger.error(
            "unhandled backend error: %s",
            redact_uri_passwords(f"{type(exc).__name__}: {exc}"),
        )
        raise InvokeException(
            json.dumps(
                {
                    "code": "INTERNAL",
                    "message": "Terjadi kesalahan internal. Silakan coba lagi.",
                    "details": {"error": type(exc).__name__},
                },
                ensure_ascii=False,
            )
        ) from None
