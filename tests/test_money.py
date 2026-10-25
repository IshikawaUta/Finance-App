from decimal import Decimal

import pytest

from finance_app.errors import AppError
from finance_app.money import from_minor_units, to_minor_units, validate_currency


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        (1, 100),
        ("12500.50", 1_250_050),
        (Decimal("0.01"), 1),
        (10.005, 1_001),  # half-up rounding
    ],
)
def test_to_minor_units(value: object, expected: int) -> None:
    assert to_minor_units(value) == expected  # type: ignore[arg-type]


def test_from_minor_units() -> None:
    assert from_minor_units(1_250_050) == Decimal("12500.50")


def test_rejects_invalid_amounts() -> None:
    with pytest.raises(AppError):
        to_minor_units("not-a-number")
    with pytest.raises(AppError):
        to_minor_units(10**20)


@pytest.mark.parametrize("code", ["idr", "USD", "eur"])
def test_validate_currency(code: str) -> None:
    assert validate_currency(code) == code.upper()


@pytest.mark.parametrize("code", ["", "RUPIAH", "12"])
def test_validate_currency_rejects(code: str) -> None:
    with pytest.raises(AppError):
        validate_currency(code)
