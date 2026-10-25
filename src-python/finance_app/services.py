"""Business logic: wallets, transactions, dashboard aggregation, demo data.

The command layer is intentionally thin; everything in this module is pure
application logic and can be unit-tested with a Mongo test database.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from beanie import PydanticObjectId
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from finance_app.config import AppConfig
from finance_app.constants import DEFAULT_CATEGORIES
from finance_app.errors import AppError
from finance_app.models import (
    Transaction,
    TransactionType,
    User,
    Wallet,
    WalletType,
    utcnow,
)
from finance_app.money import to_minor_units
from finance_app.periods import iter_buckets, resolve_period
from finance_app.schemas import (
    CashflowPoint,
    CategoriesResponse,
    CategorySlice,
    DashboardRequest,
    DashboardResponse,
    OkResponse,
    PeriodInfo,
    Summary,
    TransactionCreateRequest,
    TransactionListRequest,
    TransactionListResponse,
    TransactionOut,
    TransactionUpdateRequest,
    WalletCreateRequest,
    WalletDeleteRequest,
    WalletListResponse,
    WalletOut,
    WalletUpdateRequest,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_object_id(value: str, label: str = "data") -> PydanticObjectId:
    if not ObjectId.is_valid(value):
        raise AppError("VALIDATION_ERROR", f"ID {label} tidak valid.")
    return PydanticObjectId(value)


def _normalise_occurred_at(value: datetime | None, tz: ZoneInfo) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=tz)
    return value.astimezone(timezone.utc)


def _day_start(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc)


def _wallet_out(wallet: Wallet, balance_cents: int) -> WalletOut:
    return WalletOut(
        id=str(wallet.id),
        name=wallet.name,
        type=wallet.type.value,
        currency=wallet.currency,
        initial_balance_cents=wallet.initial_balance_cents,
        balance_cents=balance_cents,
        color=wallet.color,
        icon=wallet.icon,
        archived=wallet.archived,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
    )


async def _get_wallet(user_id: PydanticObjectId, wallet_id: str) -> Wallet:
    wallet = await Wallet.get(parse_object_id(wallet_id, "dompet"))
    if wallet is None or wallet.user_id != user_id:
        raise AppError("NOT_FOUND", "Dompet tidak ditemukan.")
    return wallet


async def _get_transaction(user_id: PydanticObjectId, transaction_id: str) -> Transaction:
    transaction = await Transaction.get(parse_object_id(transaction_id, "transaksi"))
    if transaction is None or transaction.user_id != user_id:
        raise AppError("NOT_FOUND", "Transaksi tidak ditemukan.")
    return transaction


async def _assert_wallet_name_available(
    user_id: PydanticObjectId,
    name: str,
    *,
    exclude_id: PydanticObjectId | None = None,
) -> None:
    query: dict[str, Any] = {
        "user_id": user_id,
        "name": {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"},
    }
    if exclude_id is not None:
        query["_id"] = {"$ne": exclude_id}
    if await Wallet.find_one(query) is not None:
        raise AppError("WALLET_NAME_TAKEN", "Nama dompet sudah digunakan.")


async def wallet_balances(
    user_id: PydanticObjectId,
    wallet_ids: list[PydanticObjectId] | None = None,
) -> dict[str, int]:
    """Return ``{wallet_id: balance_cents}`` in one aggregation."""

    match: dict[str, Any] = {"user_id": user_id}
    if wallet_ids is not None:
        match["wallet_id"] = {"$in": wallet_ids}

    pipeline: list[dict[str, Any]] = [
        {"$match": match},
        {
            "$group": {
                "_id": "$wallet_id",
                "income": {
                    "$sum": {
                        "$cond": [{"$eq": ["$type", TransactionType.income.value]}, "$amount_cents", 0]
                    }
                },
                "expense": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$type", TransactionType.expense.value]},
                            "$amount_cents",
                            0,
                        ]
                    }
                },
            }
        },
    ]
    cursor = await Transaction.get_pymongo_collection().aggregate(pipeline)
    rows = await cursor.to_list(length=None)

    result: dict[str, int] = {}
    for row in rows:
        result[str(row["_id"])] = int(row["income"]) - int(row["expense"])
    return result


async def _totals(match: dict[str, Any]) -> tuple[int, int, int]:
    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$type",
                "total": {"$sum": "$amount_cents"},
                "count": {"$sum": 1},
            }
        },
    ]
    cursor = await Transaction.get_pymongo_collection().aggregate(pipeline)
    rows = await cursor.to_list(length=None)

    income = 0
    expense = 0
    count = 0
    for row in rows:
        count += int(row["count"])
        if row["_id"] == TransactionType.income.value:
            income = int(row["total"])
        elif row["_id"] == TransactionType.expense.value:
            expense = int(row["total"])
    return income, expense, count


def _change_pct(current: int, previous: int) -> float | None:
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return round((current - previous) / previous * 100, 1)


# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------


async def list_wallets(user: User, *, include_archived: bool = False) -> WalletListResponse:
    query: dict[str, Any] = {"user_id": user.id}
    if not include_archived:
        query["archived"] = False

    wallets = await Wallet.find(query).sort([("created_at", 1), ("_id", 1)]).to_list()
    balances = await wallet_balances(user.id)
    items = [
        _wallet_out(wallet, wallet.initial_balance_cents + balances.get(str(wallet.id), 0))
        for wallet in wallets
    ]
    return WalletListResponse(
        wallets=items,
        total_balance_cents=sum(item.balance_cents for item in items if not item.archived),
    )


async def create_wallet(user: User, body: WalletCreateRequest) -> WalletOut:
    if body.currency != user.base_currency:
        raise AppError(
            "UNSUPPORTED_CURRENCY",
            f"Mata uang dompet harus sama dengan mata uang akun ({user.base_currency}).",
        )
    await _assert_wallet_name_available(user.id, body.name)

    wallet = Wallet(
        user_id=user.id,
        name=body.name.strip(),
        type=WalletType(body.type),
        currency=body.currency,
        initial_balance_cents=body.initial_balance_cents,
        color=body.color,
        icon=body.icon,
    )
    try:
        await wallet.insert()
    except DuplicateKeyError as exc:
        raise AppError("WALLET_NAME_TAKEN", "Nama dompet sudah digunakan.") from exc

    return _wallet_out(wallet, wallet.initial_balance_cents)


async def update_wallet(user: User, body: WalletUpdateRequest) -> WalletOut:
    wallet = await _get_wallet(user.id, body.wallet_id)

    if body.name is not None and body.name.strip() != wallet.name:
        await _assert_wallet_name_available(user.id, body.name, exclude_id=wallet.id)
        wallet.name = body.name.strip()
    if body.type is not None:
        wallet.type = WalletType(body.type)
    if body.initial_balance_cents is not None:
        wallet.initial_balance_cents = body.initial_balance_cents
    if body.color is not None:
        wallet.color = body.color
    if body.icon is not None:
        wallet.icon = body.icon
    if body.archived is not None:
        wallet.archived = body.archived
    wallet.updated_at = utcnow()
    await wallet.save()

    balances = await wallet_balances(user.id, [wallet.id])
    balance = wallet.initial_balance_cents + balances.get(str(wallet.id), 0)
    return _wallet_out(wallet, balance)


async def delete_wallet(user: User, body: WalletDeleteRequest) -> OkResponse:
    wallet = await _get_wallet(user.id, body.wallet_id)
    count = await Transaction.find({"user_id": user.id, "wallet_id": wallet.id}).count()

    if count > 0 and not body.delete_transactions:
        raise AppError(
            "WALLET_NOT_EMPTY",
            f"Dompet masih memiliki {count} transaksi. Hapus transaksinya atau arsipkan dompet.",
            details={"transaction_count": count},
        )

    if count > 0:
        await Transaction.find({"user_id": user.id, "wallet_id": wallet.id}).delete()
    await wallet.delete()
    return OkResponse(message="Dompet dihapus.")


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


async def _wallet_names(wallet_ids: list[PydanticObjectId]) -> dict[str, str]:
    if not wallet_ids:
        return {}
    wallets = await Wallet.find({"_id": {"$in": wallet_ids}}).to_list()
    return {str(wallet.id): wallet.name for wallet in wallets}


async def create_transaction(user: User, body: TransactionCreateRequest, config: AppConfig) -> TransactionOut:
    wallet = await _get_wallet(user.id, body.wallet_id)
    if wallet.archived:
        raise AppError("WALLET_ARCHIVED", "Dompet ini sedang diarsipkan.")

    transaction = Transaction(
        user_id=user.id,
        wallet_id=wallet.id,
        type=TransactionType(body.type),
        amount_cents=body.amount_cents,
        category=body.category.strip(),
        note=body.note.strip(),
        occurred_at=_normalise_occurred_at(body.occurred_at, config.tz),
    )
    await transaction.insert()
    return TransactionOut.from_doc(transaction, wallet.name)


async def update_transaction(
    user: User,
    body: TransactionUpdateRequest,
    config: AppConfig,
) -> TransactionOut:
    transaction = await _get_transaction(user.id, body.transaction_id)

    if body.wallet_id is not None and body.wallet_id != str(transaction.wallet_id):
        wallet = await _get_wallet(user.id, body.wallet_id)
        if wallet.archived:
            raise AppError("WALLET_ARCHIVED", "Dompet ini sedang diarsipkan.")
        transaction.wallet_id = wallet.id
    if body.type is not None:
        transaction.type = TransactionType(body.type)
    if body.amount_cents is not None:
        transaction.amount_cents = body.amount_cents
    if body.category is not None:
        transaction.category = body.category.strip()
    if body.note is not None:
        transaction.note = body.note.strip()
    if body.occurred_at is not None:
        transaction.occurred_at = _normalise_occurred_at(body.occurred_at, config.tz)

    transaction.updated_at = utcnow()
    await transaction.save()

    wallet = await Wallet.get(transaction.wallet_id)
    return TransactionOut.from_doc(transaction, wallet.name if wallet else "Dompet dihapus")


async def delete_transaction(user: User, transaction_id: str) -> OkResponse:
    transaction = await _get_transaction(user.id, transaction_id)
    await transaction.delete()
    return OkResponse(message="Transaksi dihapus.")


def _transaction_match(user: User, body: TransactionListRequest, config: AppConfig) -> dict[str, Any]:
    match: dict[str, Any] = {"user_id": user.id}

    if body.wallet_ids:
        if len(body.wallet_ids) > 50:
            raise AppError("VALIDATION_ERROR", "Maksimal 50 dompet per filter.")
        match["wallet_id"] = {"$in": [parse_object_id(value, "dompet") for value in body.wallet_ids]}
    if body.types:
        match["type"] = {"$in": list(body.types)}
    if body.categories:
        match["category"] = {"$in": body.categories}

    if body.date_from is not None or body.date_to is not None:
        range_filter: dict[str, Any] = {}
        if body.date_from is not None:
            range_filter["$gte"] = _day_start(body.date_from, config.tz)
        if body.date_to is not None:
            range_filter["$lt"] = _day_start(body.date_to + timedelta(days=1), config.tz)
        if body.date_from is not None and body.date_to is not None and body.date_from > body.date_to:
            raise AppError("VALIDATION_ERROR", "Tanggal awal tidak boleh setelah tanggal akhir.")
        match["occurred_at"] = range_filter

    if body.search:
        pattern = re.escape(body.search.strip())
        match["$or"] = [
            {"note": {"$regex": pattern, "$options": "i"}},
            {"category": {"$regex": pattern, "$options": "i"}},
        ]
    return match


async def list_transactions(
    user: User,
    body: TransactionListRequest,
    config: AppConfig,
) -> TransactionListResponse:
    match = _transaction_match(user, body, config)
    sort_field = body.sort_by
    direction = -1 if body.sort_dir == "desc" else 1
    skip = (body.page - 1) * body.page_size

    find_query = (
        Transaction.find(match)
        .sort([(sort_field, direction), ("_id", direction)])
        .skip(skip)
        .limit(body.page_size)
    )

    items, total, (income, expense, _count) = await asyncio.gather(
        find_query.to_list(),
        Transaction.find(match).count(),
        _totals(match),
    )

    names = await _wallet_names([transaction.wallet_id for transaction in items])
    return TransactionListResponse(
        items=[
            TransactionOut.from_doc(transaction, names.get(str(transaction.wallet_id), "—"))
            for transaction in items
        ],
        total=total,
        page=body.page,
        page_size=body.page_size,
        pages=math.ceil(total / body.page_size) if total else 0,
        income_cents=income,
        expense_cents=expense,
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


async def _cashflow_series(
    match: dict[str, Any],
    *,
    start: datetime,
    end: datetime,
    granularity: str,
    tz: ZoneInfo,
) -> list[CashflowPoint]:
    date_trunc: dict[str, Any] = {
        "date": "$occurred_at",
        "unit": granularity,
        "timezone": str(tz),
    }
    if granularity == "week":
        date_trunc["startOfWeek"] = "monday"

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {"$dateTrunc": date_trunc},
                "income": {
                    "$sum": {
                        "$cond": [{"$eq": ["$type", TransactionType.income.value]}, "$amount_cents", 0]
                    }
                },
                "expense": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$type", TransactionType.expense.value]},
                            "$amount_cents",
                            0,
                        ]
                    }
                },
            }
        },
        {"$sort": {"_id": 1}},
    ]
    cursor = await Transaction.get_pymongo_collection().aggregate(pipeline)
    rows = await cursor.to_list(length=None)

    by_day: dict[date, tuple[int, int]] = {}
    for row in rows:
        moment = row["_id"]
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        by_day[moment.astimezone(tz).date()] = (int(row["income"]), int(row["expense"]))

    points: list[CashflowPoint] = []
    for day in iter_buckets(start, end, tz, granularity):  # type: ignore[arg-type]
        income, expense = by_day.get(day, (0, 0))
        bucket_utc = datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc)
        points.append(
            CashflowPoint(
                bucket_start=bucket_utc,
                label=day.isoformat(),
                income_cents=income,
                expense_cents=expense,
                net_cents=income - expense,
            )
        )
    return points


async def _expense_by_category(match: dict[str, Any]) -> list[CategorySlice]:
    pipeline = [
        {"$match": {**match, "type": TransactionType.expense.value}},
        {"$group": {"_id": "$category", "amount": {"$sum": "$amount_cents"}}},
        {"$sort": {"amount": -1}},
    ]
    cursor = await Transaction.get_pymongo_collection().aggregate(pipeline)
    rows = await cursor.to_list(length=None)
    total = sum(int(row["amount"]) for row in rows)
    if total <= 0:
        return []

    slices = [
        CategorySlice(
            category=str(row["_id"]),
            amount_cents=int(row["amount"]),
            percentage=round(int(row["amount"]) / total * 100, 1),
        )
        for row in rows
    ]

    if len(slices) > 8:
        head = slices[:7]
        rest = sum(slice_.amount_cents for slice_ in slices[7:])
        others = next((slice_ for slice_ in head if slice_.category == "Lainnya"), None)
        if others is not None:
            others.amount_cents += rest
            others.percentage = round(others.amount_cents / total * 100, 1)
        else:
            head.append(
                CategorySlice(
                    category="Lainnya",
                    amount_cents=rest,
                    percentage=round(rest / total * 100, 1),
                )
            )
        slices = head
    return slices


async def _recent_transactions(
    user: User,
    wallet_ids: list[PydanticObjectId] | None,
    limit: int = 6,
) -> list[TransactionOut]:
    query: dict[str, Any] = {"user_id": user.id}
    if wallet_ids:
        query["wallet_id"] = {"$in": wallet_ids}
    items = await Transaction.find(query).sort([("occurred_at", -1), ("_id", -1)]).limit(limit).to_list()
    names = await _wallet_names([transaction.wallet_id for transaction in items])
    return [
        TransactionOut.from_doc(transaction, names.get(str(transaction.wallet_id), "—"))
        for transaction in items
    ]


async def dashboard(user: User, body: DashboardRequest, config: AppConfig) -> DashboardResponse:
    tz = config.tz
    period = resolve_period(
        body.period,
        tz=tz,
        date_from=body.date_from,
        date_to=body.date_to,
    )

    wallet_filter: list[PydanticObjectId] | None = None
    if body.wallet_ids:
        wallet_filter = [parse_object_id(value, "dompet") for value in body.wallet_ids]

    wallets_response = await list_wallets(user)
    total_balance = wallets_response.total_balance_cents

    period_match: dict[str, Any] = {
        "user_id": user.id,
        "occurred_at": {"$gte": period.start, "$lt": period.end},
    }
    previous_match: dict[str, Any] = {
        "user_id": user.id,
        "occurred_at": {"$gte": period.previous_start, "$lt": period.previous_end},
    }
    if wallet_filter:
        period_match["wallet_id"] = {"$in": wallet_filter}
        previous_match["wallet_id"] = {"$in": wallet_filter}

    (income, expense, tx_count), (prev_income, prev_expense, _), cashflow, categories = (
        await asyncio.gather(
            _totals(period_match),
            _totals(previous_match),
            _cashflow_series(
                period_match,
                start=period.start,
                end=period.end,
                granularity=period.granularity,
                tz=tz,
            ),
            _expense_by_category(period_match),
        )
    )
    recent = await _recent_transactions(user, wallet_filter)

    summary = Summary(
        total_balance_cents=total_balance,
        period_income_cents=income,
        period_expense_cents=expense,
        period_net_cents=income - expense,
        previous_income_cents=prev_income,
        previous_expense_cents=prev_expense,
        income_change_pct=_change_pct(income, prev_income),
        expense_change_pct=_change_pct(expense, prev_expense),
        wallet_count=len([wallet for wallet in wallets_response.wallets if not wallet.archived]),
        transaction_count=tx_count,
    )

    return DashboardResponse(
        period=PeriodInfo(
            key=period.key,
            start=period.start,
            end=period.end,
            granularity=period.granularity,
        ),
        summary=summary,
        cashflow=cashflow,
        expense_by_category=categories,
        recent_transactions=recent,
        wallets=wallets_response.wallets,
    )


# ---------------------------------------------------------------------------
# Categories & demo data
# ---------------------------------------------------------------------------


async def categories(user: User) -> CategoriesResponse:
    collection = Transaction.get_pymongo_collection()
    income_used, expense_used = await asyncio.gather(
        collection.distinct("category", {"user_id": user.id, "type": "income"}),
        collection.distinct("category", {"user_id": user.id, "type": "expense"}),
    )

    def merge(defaults: tuple[str, ...], used: list[Any]) -> list[str]:
        values = list(defaults)
        for value in used:
            if isinstance(value, str) and value and value not in values:
                values.append(value)
        return values

    return CategoriesResponse(
        income=merge(DEFAULT_CATEGORIES["income"], income_used),
        expense=merge(DEFAULT_CATEGORIES["expense"], expense_used),
    )


_DEMO_EXPENSES = (
    ("Makanan", "Makan siang", 25_000, 75_000),
    ("Transportasi", "Gojek / bensin", 15_000, 60_000),
    ("Belanja", "Belanja bulanan", 80_000, 350_000),
    ("Tagihan", "Listrik & internet", 100_000, 400_000),
    ("Kesehatan", "Vitamin / obat", 40_000, 150_000),
    ("Hiburan", "Langganan streaming", 30_000, 120_000),
    ("Pendidikan", "Buku / kursus", 75_000, 250_000),
    ("Rumah", "Perlengkapan rumah", 50_000, 200_000),
)


async def seed_demo(user: User, config: AppConfig) -> OkResponse:
    if await Wallet.find({"user_id": user.id}).count() > 0:
        return OkResponse(message="Data contoh hanya dapat dibuat pada akun tanpa dompet.")

    wallets = [
        Wallet(
            user_id=user.id,
            name="Dompet Tunai",
            type=WalletType.cash,
            currency=user.base_currency,
            initial_balance_cents=to_minor_units(500_000),
            color="#10b981",
            icon="wallet",
        ),
        Wallet(
            user_id=user.id,
            name="Bank Utama",
            type=WalletType.bank,
            currency=user.base_currency,
            initial_balance_cents=to_minor_units(7_500_000),
            color="#3b82f6",
            icon="bank",
        ),
        Wallet(
            user_id=user.id,
            name="E-Wallet",
            type=WalletType.ewallet,
            currency=user.base_currency,
            initial_balance_cents=to_minor_units(350_000),
            color="#8b5cf6",
            icon="phone",
        ),
    ]
    for wallet in wallets:
        await wallet.insert()

    rng = random.Random(str(user.id))
    now = datetime.now(config.tz)
    transactions: list[Transaction] = []

    salary_day = now - timedelta(days=12)
    transactions.append(
        Transaction(
            user_id=user.id,
            wallet_id=wallets[1].id,
            type=TransactionType.income,
            amount_cents=to_minor_units(9_500_000),
            category="Gaji",
            note="Gaji bulanan",
            occurred_at=salary_day.astimezone(timezone.utc),
        )
    )
    transactions.append(
        Transaction(
            user_id=user.id,
            wallet_id=wallets[2].id,
            type=TransactionType.income,
            amount_cents=to_minor_units(1_750_000),
            category="Freelance",
            note="Proyek desain",
            occurred_at=(now - timedelta(days=6)).astimezone(timezone.utc),
        )
    )

    for _ in range(44):
        days_ago = rng.randint(0, 74)
        category, note, low, high = rng.choice(_DEMO_EXPENSES)
        occurred = (now - timedelta(days=days_ago)).replace(
            hour=rng.randint(7, 21),
            minute=rng.randint(0, 59),
            second=0,
            microsecond=0,
        )
        wallet = rng.choice(wallets)
        transactions.append(
            Transaction(
                user_id=user.id,
                wallet_id=wallet.id,
                type=TransactionType.expense,
                amount_cents=to_minor_units(rng.randint(low, high)),
                category=category,
                note=note,
                occurred_at=occurred.astimezone(timezone.utc),
            )
        )

    await Transaction.insert_many(transactions)
    return OkResponse(
        message=(
            f"Data contoh dibuat: {len(wallets)} dompet dan {len(transactions)} transaksi."
        )
    )
