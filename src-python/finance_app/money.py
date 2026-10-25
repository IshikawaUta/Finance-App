"""Money helpers.

All monetary values are stored as integer **minor units** (cents) to avoid
binary floating point errors.  For IDR the UI hides decimals, but the storage
format stays currency-agnostic (2 decimal places).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from finance_app.errors import AppError

MINOR_UNIT_EXPONENT = 2
MINOR_UNIT_FACTOR = 10**MINOR_UNIT_EXPONENT
MAX_AMOUNT_CENTS = 10**15


def validate_currency(code: str) -> str:
    code = code.strip().upper()
    if len(code) != 3 or not code.isalpha():
        raise AppError("VALIDATION_ERROR", "Kode mata uang harus 3 huruf, mis. IDR atau USD.")
    return code


def to_minor_units(amount: Decimal | int | float | str) -> int:
    """Convert a major-unit amount (e.g. ``12.50``) into cents."""

    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError) as exc:
        raise AppError("VALIDATION_ERROR", "Nominal tidak valid.") from exc

    if not value.is_finite():
        raise AppError("VALIDATION_ERROR", "Nominal tidak valid.")

    cents = int((value * MINOR_UNIT_FACTOR).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if abs(cents) > MAX_AMOUNT_CENTS:
        raise AppError("VALIDATION_ERROR", "Nominal terlalu besar.")
    return cents


def from_minor_units(cents: int) -> Decimal:
    """Convert cents back to a major-unit decimal."""

    return (Decimal(cents) / MINOR_UNIT_FACTOR).quantize(Decimal("0.01"))
