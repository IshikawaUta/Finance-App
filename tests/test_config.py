"""Connection strings are always masked before logging or returning them."""

from __future__ import annotations

from finance_app.config import mask_uri, redact_uri_passwords


def test_mask_uri_hides_password() -> None:
    assert (
        mask_uri("mongodb+srv://user:supersecret@cluster.example.net/finance_app")
        == "mongodb+srv://user:***@cluster.example.net/finance_app"
    )
    assert mask_uri("mongodb://:supersecret@localhost/finance_app") == (
        "mongodb://:***@localhost/finance_app"
    )


def test_mask_uri_keeps_non_credential_uris_intact() -> None:
    uri = "mongodb://localhost:27017/finance_app"
    assert mask_uri(uri) == uri
    assert mask_uri(None) is None


def test_redact_uri_passwords_works_inside_error_text() -> None:
    message = "ConfigurationError for mongodb://user:supersecret@host/db"
    redacted = redact_uri_passwords(message)
    assert "supersecret" not in redacted
    assert "mongodb://user:***@host/db" in redacted
