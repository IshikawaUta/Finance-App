"""Beanie document models.

Collections
-----------
users          : account + auth data
wallets        : one document per wallet, owned by a user
transactions   : immutable-in-shape money movements (income / expense)

All timestamps are stored in UTC.  Money is stored in integer minor units.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import ClassVar

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from finance_app.constants import DEFAULT_WALLET_COLORS


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WalletType(str, Enum):
    cash = "cash"
    bank = "bank"
    ewallet = "ewallet"
    credit = "credit"
    investment = "investment"
    other = "other"


class TransactionType(str, Enum):
    income = "income"
    expense = "expense"


class User(Document):
    email: Indexed(str, unique=True)  # type: ignore[valid-type]
    name: str = Field(min_length=1, max_length=80)
    password_hash: str
    base_currency: str = "IDR"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_login_at: datetime | None = None

    class Settings:
        name = "users"


class Wallet(Document):
    user_id: Indexed(PydanticObjectId)  # type: ignore[valid-type]
    name: str = Field(min_length=1, max_length=60)
    type: WalletType = WalletType.cash
    currency: str = "IDR"
    initial_balance_cents: int = Field(default=0, ge=0)
    color: str = DEFAULT_WALLET_COLORS[0]
    icon: str = "wallet"
    archived: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "wallets"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("user_id", ASCENDING), ("archived", ASCENDING), ("created_at", ASCENDING)],
                name="wallets_by_user",
            ),
        ]


class Transaction(Document):
    user_id: Indexed(PydanticObjectId)  # type: ignore[valid-type]
    wallet_id: Indexed(PydanticObjectId)  # type: ignore[valid-type]
    type: TransactionType
    amount_cents: int = Field(gt=0, le=10**15)
    category: str = Field(min_length=1, max_length=40)
    note: str = Field(default="", max_length=280)
    occurred_at: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "transactions"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("user_id", ASCENDING), ("occurred_at", DESCENDING)],
                name="tx_by_user_date",
            ),
            IndexModel(
                [("user_id", ASCENDING), ("wallet_id", ASCENDING), ("occurred_at", DESCENDING)],
                name="tx_by_user_wallet_date",
            ),
            IndexModel(
                [
                    ("user_id", ASCENDING),
                    ("type", ASCENDING),
                    ("category", ASCENDING),
                    ("occurred_at", DESCENDING),
                ],
                name="tx_by_user_type_category_date",
            ),
        ]


DOCUMENT_MODELS = [User, Wallet, Transaction]


__all__ = [
    "DOCUMENT_MODELS",
    "Transaction",
    "TransactionType",
    "User",
    "Wallet",
    "WalletType",
    "utcnow",
]
