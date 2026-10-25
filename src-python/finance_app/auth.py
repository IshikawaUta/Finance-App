"""Authentication primitives: Argon2id password hashing + HS256 JWTs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from bson import ObjectId

from finance_app.config import JWT_TTL_DAYS, AppConfig
from finance_app.errors import AppError
from finance_app.models import User

_ISSUER = "finance-app"
_ALGORITHM = "HS256"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """Burn the same CPU time for unknown accounts (timing attack mitigation)."""

    return _hasher.hash("this-is-not-a-real-password")


def burn_password_time() -> None:
    verify_password(_dummy_hash(), "wrong-password")


def create_access_token(
    user_id: ObjectId,
    config: AppConfig,
    *,
    now: datetime | None = None,
) -> tuple[str, datetime]:
    issued_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    expires_at = issued_at + timedelta(days=JWT_TTL_DAYS)
    payload = {
        "sub": str(user_id),
        "iss": _ISSUER,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, config.jwt_secret, algorithm=_ALGORITHM)
    return token, expires_at


def decode_access_token(token: str, config: AppConfig) -> str:
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[_ALGORITHM],
            issuer=_ISSUER,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError("AUTH_EXPIRED", "Sesi sudah berakhir. Silakan masuk kembali.") from exc
    except jwt.InvalidTokenError as exc:
        raise AppError("AUTH_INVALID_TOKEN", "Sesi tidak valid. Silakan masuk kembali.") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not ObjectId.is_valid(subject):
        raise AppError("AUTH_INVALID_TOKEN", "Sesi tidak valid. Silakan masuk kembali.")
    return subject


async def require_user(token: str, config: AppConfig) -> User:
    user_id = decode_access_token(token, config)
    user = await User.get(ObjectId(user_id))
    if user is None:
        raise AppError("AUTH_INVALID_TOKEN", "Akun tidak ditemukan. Silakan masuk kembali.")
    return user
