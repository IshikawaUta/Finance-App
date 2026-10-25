"""Database reconfiguration keeps config and live state consistent."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import ClassVar

import pytest

from finance_app.config import AppConfig
from finance_app.state import AppState


class FakeDatabase:
    instances: ClassVar[list[FakeDatabase]] = []

    def __init__(self) -> None:
        self.connected = False
        self.disconnected = False
        self.last_error: str | None = None
        FakeDatabase.instances.append(self)

    async def connect(self, uri: str, db_name: str) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False
        self.disconnected = True

    async def ping(self) -> float:
        return 1.0


def _config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        mongodb_uri="mongodb://old",
        mongodb_db="old_db",
        jwt_secret="x" * 32,
        timezone="Asia/Jakarta",
        log_level="INFO",
        data_dir=tmp_path,
        config_path=tmp_path / "config.json",
        source="env",
    )


def test_reconfigure_swaps_after_persisting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeDatabase.instances.clear()
    monkeypatch.setattr("finance_app.state.Database", FakeDatabase)
    old_db = FakeDatabase()
    state = AppState(config=_config(tmp_path), db=old_db)

    status = asyncio.run(state.reconfigure("mongodb://new", "new_db"))
    candidate = FakeDatabase.instances[-1]

    assert state.db is candidate
    assert old_db.disconnected
    assert state.config.mongodb_db == "new_db"
    assert state.config.source == "file"
    assert status.db_connected
    assert status.db_name == "new_db"
    assert '"mongodb_db": "new_db"' in (tmp_path / "config.json").read_text(encoding="utf-8")


def test_reconfigure_keeps_old_connection_when_save_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeDatabase.instances.clear()
    monkeypatch.setattr("finance_app.state.Database", FakeDatabase)
    old_db = FakeDatabase()
    state = AppState(config=_config(tmp_path), db=old_db)

    def fail_save(*args: object, **kwargs: object) -> AppConfig:
        raise OSError("disk full")

    monkeypatch.setattr("finance_app.state.save_connection", fail_save)

    with pytest.raises(OSError, match="disk full"):
        asyncio.run(state.reconfigure("mongodb://new", "new_db"))

    candidate = FakeDatabase.instances[-1]
    assert state.db is old_db
    assert not old_db.disconnected
    assert candidate.disconnected
    assert state.config.mongodb_db == "old_db"
    assert not (tmp_path / "config.json").exists()
