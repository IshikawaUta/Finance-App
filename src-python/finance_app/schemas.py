"""Pydantic request/response models — the IPC contract.

Field names are snake_case on both sides of the bridge.  This keeps the
contract mechanically identical to the Python models (PyTauri serializes with
``model_dump_json``) and avoids subtle camelCase alias bugs.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from finance_app.models import Transaction, User
from finance_app.money import validate_currency

SortBy = Literal["occurred_at", "amount_cents", "created_at"]
SortDir = Literal["asc", "desc"]
TransactionKind = Literal["income", "expense"]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ApiResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")


class TokenRequest(ApiModel):
    token: str = Field(min_length=10, max_length=4096)


class HealthResponse(ApiResponse):
    status: str = "ok"
    version: str
    uptime_seconds: float


class UserOut(ApiResponse):
    id: str
    email: str
    name: str
    base_currency: str
    created_at: datetime

    @classmethod
    def from_doc(cls, user: User) -> UserOut:
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            base_currency=user.base_currency,
            created_at=user.created_at,
        )


class RegisterRequest(ApiModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    base_currency: str = "IDR"

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("base_currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        return validate_currency(value)


class LoginRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class AuthResponse(ApiResponse):
    token: str
    expires_at: datetime
    user: UserOut


class OkResponse(ApiResponse):
    ok: bool = True
    message: str = ""


class WalletOut(ApiResponse):
    id: str
    name: str
    type: str
    currency: str
    initial_balance_cents: int
    balance_cents: int
    color: str
    icon: str
    archived: bool
    created_at: datetime
    updated_at: datetime


class WalletListResponse(ApiResponse):
    wallets: list[WalletOut]
    total_balance_cents: int


class WalletCreateRequest(ApiModel):
    token: str = Field(min_length=10, max_length=4096)
    name: str = Field(min_length=1, max_length=60)
    type: Literal["cash", "bank", "ewallet", "credit", "investment", "other"] = "cash"
    currency: str = "IDR"
    initial_balance_cents: int = Field(default=0, ge=0, le=10**15)
    color: str = Field(default="#10b981", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str = Field(default="wallet", max_length=30)

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        return validate_currency(value)


class WalletUpdateRequest(ApiModel):
    token: str = Field(min_length=10, max_length=4096)
    wallet_id: str
    name: str | None = Field(default=None, min_length=1, max_length=60)
    type: Literal["cash", "bank", "ewallet", "credit", "investment", "other"] | None = None
    initial_balance_cents: int | None = Field(default=None, ge=0, le=10**15)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str | None = Field(default=None, max_length=30)
    archived: bool | None = None


class WalletDeleteRequest(ApiModel):
    token: str = Field(min_length=10, max_length=4096)
    wallet_id: str
    delete_transactions: bool = False


class TransactionOut(ApiResponse):
    id: str
    wallet_id: str
    wallet_name: str
    type: str
    amount_cents: int
    category: str
    note: str
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_doc(cls, tx: Transaction, wallet_name: str) -> TransactionOut:
        return cls(
            id=str(tx.id),
            wallet_id=str(tx.wallet_id),
            wallet_name=wallet_name,
            type=tx.type.value,
            amount_cents=tx.amount_cents,
            category=tx.category,
            note=tx.note,
            occurred_at=tx.occurred_at,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )


class TransactionCreateRequest(ApiModel):
    token: str = Field(min_length=10, max_length=4096)
    wallet_id: str
    type: TransactionKind
    amount_cents: int = Field(gt=0, le=10**15)
    category: str = Field(min_length=1, max_length=40)
    note: str = Field(default="", max_length=280)
    occurred_at: datetime | None = None


class TransactionUpdateRequest(ApiModel):
    token: str = Field(min_length=10, max_length=4096)
    transaction_id: str
    wallet_id: str | None = None
    type: TransactionKind | None = None
    amount_cents: int | None = Field(default=None, gt=0, le=10**15)
    category: str | None = Field(default=None, min_length=1, max_length=40)
    note: str | None = Field(default=None, max_length=280)
    occurred_at: datetime | None = None


class TransactionDeleteRequest(ApiModel):
    token: str = Field(min_length=10, max_length=4096)
    transaction_id: str


class TransactionListRequest(ApiModel):
    token: str = Field(min_length=10, max_length=4096)
    wallet_ids: list[str] = Field(default_factory=list)
    types: list[TransactionKind] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = Field(default=None, max_length=100)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=200)
    sort_by: SortBy = "occurred_at"
    sort_dir: SortDir = "desc"


class TransactionListResponse(ApiResponse):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int
    pages: int
    income_cents: int
    expense_cents: int


class DashboardRequest(ApiModel):
    token: str = Field(min_length=10, max_length=4096)
    period: Literal[
        "this_week",
        "this_month",
        "last_month",
        "last_7_days",
        "last_30_days",
        "this_year",
        "custom",
    ] = "this_month"
    date_from: date | None = None
    date_to: date | None = None
    wallet_ids: list[str] = Field(default_factory=list)


class PeriodInfo(ApiResponse):
    key: str
    start: datetime
    end: datetime
    granularity: str


class Summary(ApiResponse):
    total_balance_cents: int
    period_income_cents: int
    period_expense_cents: int
    period_net_cents: int
    previous_income_cents: int
    previous_expense_cents: int
    income_change_pct: float | None
    expense_change_pct: float | None
    wallet_count: int
    transaction_count: int


class CashflowPoint(ApiResponse):
    bucket_start: datetime
    label: str
    income_cents: int
    expense_cents: int
    net_cents: int


class CategorySlice(ApiResponse):
    category: str
    amount_cents: int
    percentage: float


class DashboardResponse(ApiResponse):
    period: PeriodInfo
    summary: Summary
    cashflow: list[CashflowPoint]
    expense_by_category: list[CategorySlice]
    recent_transactions: list[TransactionOut]
    wallets: list[WalletOut]


class CategoriesResponse(ApiResponse):
    income: list[str]
    expense: list[str]


class SystemStatus(ApiResponse):
    app_version: str
    python_version: str
    db_connected: bool
    db_latency_ms: float | None
    db_name: str
    db_uri_masked: str | None
    config_source: str
    data_dir: str
    last_error: str | None
    offline: bool


class SetConnectionRequest(ApiModel):
    uri: str = Field(min_length=12, max_length=2048)
    db_name: str = Field(default="finance_app", pattern=r"^[A-Za-z0-9_-]{1,64}$")

    @field_validator("uri")
    @classmethod
    def _validate_uri(cls, value: str) -> str:
        if not value.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("URI harus diawali mongodb:// atau mongodb+srv://")
        return value
