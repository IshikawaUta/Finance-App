"""IPC error serialization without a running PyTauri interpreter."""

from __future__ import annotations

import json
import logging
import sys
import types

import pytest
from pydantic import BaseModel, field_validator

from finance_app.errors import AppError, api_errors


def _install_fake_pytauri(monkeypatch: pytest.MonkeyPatch) -> type[Exception]:
    fake_pkg = types.ModuleType("pytauri")
    fake_pkg.__path__ = []  # type: ignore[attr-defined]
    fake_ipc = types.ModuleType("pytauri.ipc")

    class FakeInvokeException(Exception):
        def __init__(self, value: str) -> None:
            super().__init__(value)
            self.value = value

    fake_ipc.InvokeException = FakeInvokeException  # type: ignore[attr-defined]
    fake_pkg.ipc = fake_ipc  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pytauri", fake_pkg)
    monkeypatch.setitem(sys.modules, "pytauri.ipc", fake_ipc)
    return FakeInvokeException


def test_invoke_exception_comes_from_pytauri_ipc(monkeypatch: pytest.MonkeyPatch) -> None:
    """PyTauri 0.8 exports InvokeException from pytauri.ipc, not pytauri."""

    fake_invoke_exception = _install_fake_pytauri(monkeypatch)

    invoke = AppError("TEST", "Pesan uji", details={"field": "email"}).to_invoke()
    assert isinstance(invoke, fake_invoke_exception)
    assert json.loads(invoke.value) == {
        "code": "TEST",
        "message": "Pesan uji",
        "details": {"field": "email"},
    }

    with pytest.raises(fake_invoke_exception) as exc_info, api_errors():
        raise AppError("TEST_2", "Pesan kedua")

    assert json.loads(exc_info.value.value)["code"] == "TEST_2"


class _SecretPayload(BaseModel):
    uri: str

    @field_validator("uri")
    @classmethod
    def _reject(cls, value: str) -> str:
        raise ValueError("URI tidak valid")


def test_validation_errors_do_not_echo_secrets(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Validation failures must not leak the connection string or its password."""

    fake_invoke_exception = _install_fake_pytauri(monkeypatch)
    secret = "mongodb+srv://user:supersecret@cluster.example.net/"

    with (
        caplog.at_level(logging.INFO),
        pytest.raises(fake_invoke_exception) as exc_info,
        api_errors(),
    ):
        _SecretPayload(uri=secret)

    assert "supersecret" not in exc_info.value.value
    assert "supersecret" not in caplog.text
    payload = json.loads(exc_info.value.value)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["details"]["errors"] == [
        {
            "type": "value_error",
            "loc": ["uri"],
            "msg": "Value error, URI tidak valid",
        }
    ]
