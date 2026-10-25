from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from bson import ObjectId

from finance_app.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from finance_app.config import AppConfig
from finance_app.errors import AppError


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        mongodb_uri=None,
        mongodb_db="finance_app",
        jwt_secret="x" * 64,
        timezone="Asia/Jakarta",
        log_level="INFO",
        data_dir=tmp_path,
        config_path=tmp_path / "config.json",
        source="missing",
    )


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("rahasia123")
    assert hashed != "rahasia123"
    assert verify_password(hashed, "rahasia123")
    assert not verify_password(hashed, "salah-password")


def test_jwt_roundtrip(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    user_id = ObjectId()
    token, expires_at = create_access_token(user_id, config)

    assert decode_access_token(token, config) == str(user_id)
    assert expires_at > datetime.now(timezone.utc)


def test_expired_token_is_rejected(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    token, _ = create_access_token(
        ObjectId(),
        config,
        now=datetime.now(timezone.utc) - timedelta(days=45),
    )

    with pytest.raises(AppError) as exc:
        decode_access_token(token, config)
    assert exc.value.code == "AUTH_EXPIRED"


def test_token_signed_with_other_secret_is_rejected(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    other = AppConfig(
        mongodb_uri=None,
        mongodb_db="finance_app",
        jwt_secret="y" * 64,
        timezone="Asia/Jakarta",
        log_level="INFO",
        data_dir=tmp_path,
        config_path=tmp_path / "config.json",
        source="missing",
    )
    token, _ = create_access_token(ObjectId(), config)

    with pytest.raises(AppError) as exc:
        decode_access_token(token, other)
    assert exc.value.code == "AUTH_INVALID_TOKEN"


def test_timezone_property_falls_back_to_utc(tmp_path: Path) -> None:
    config = AppConfig(
        mongodb_uri=None,
        mongodb_db="finance_app",
        jwt_secret="x" * 64,
        timezone="Mars/Olympus",
        log_level="INFO",
        data_dir=tmp_path,
        config_path=tmp_path / "config.json",
        source="missing",
    )
    assert config.tz == ZoneInfo("UTC")
