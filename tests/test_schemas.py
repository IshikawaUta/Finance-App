import pytest
from pydantic import ValidationError

from finance_app.schemas import (
    RegisterRequest,
    SetConnectionRequest,
    TransactionCreateRequest,
    WalletCreateRequest,
)


def test_email_is_normalised() -> None:
    request = RegisterRequest(
        email="  Test.User@Example.COM ",
        name="Uta",
        password="rahasia123",
    )
    assert request.email == "test.user@example.com"


def test_short_password_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.co", name="Uta", password="short")


def test_wallet_color_must_be_hex() -> None:
    with pytest.raises(ValidationError):
        WalletCreateRequest(token="x" * 20, name="Tunai", color="green")


def test_transaction_amount_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        TransactionCreateRequest(
            token="x" * 20,
            wallet_id="0" * 24,
            type="expense",
            amount_cents=0,
            category="Makanan",
        )


def test_connection_uri_scheme() -> None:
    with pytest.raises(ValidationError):
        SetConnectionRequest(uri="https://example.com")

    request = SetConnectionRequest(
        uri="mongodb+srv://user:pass@cluster.mongodb.net/",
        db_name="finance_app",
    )
    assert request.db_name == "finance_app"


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="a@b.co",
            name="Uta",
            password="rahasia123",
            is_admin=True,
        )
