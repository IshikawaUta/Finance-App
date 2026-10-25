"""Date-range and period helpers.

Periods are computed in the user's local timezone and returned as half-open
UTC ranges ``[start, end)``.  MongoDB stores all timestamps in UTC.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from finance_app.errors import AppError

PeriodKey = Literal[
    "this_week",
    "this_month",
    "last_month",
    "last_7_days",
    "last_30_days",
    "this_year",
    "custom",
]
Granularity = Literal["day", "week", "month"]

PERIOD_KEYS: tuple[str, ...] = (
    "this_week",
    "this_month",
    "last_month",
    "last_7_days",
    "last_30_days",
    "this_year",
    "custom",
)


@dataclass(frozen=True)
class PeriodRange:
    key: str
    start: datetime
    end: datetime
    previous_start: datetime
    previous_end: datetime
    granularity: Granularity

    @property
    def days(self) -> int:
        return max(1, (self.end - self.start).days)


def _midnight(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz)


def _next_month(day: date) -> date:
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _previous_month(day: date) -> date:
    if day.month == 1:
        return date(day.year - 1, 12, 1)
    return date(day.year, day.month - 1, 1)


def _granularity_for(start: datetime, end: datetime) -> Granularity:
    days = (end - start).days
    if days <= 31:
        return "day"
    if days <= 120:
        return "week"
    return "month"


def resolve_period(
    key: str,
    *,
    tz: ZoneInfo,
    date_from: date | None = None,
    date_to: date | None = None,
    now: datetime | None = None,
) -> PeriodRange:
    """Resolve a named period (or a custom inclusive date range)."""

    current = (now or datetime.now(tz)).astimezone(tz)
    today = current.date()

    if key == "this_week":
        start_day = today - timedelta(days=today.weekday())
        start = _midnight(start_day, tz)
        end = _midnight(start_day + timedelta(days=7), tz)
        previous_start = _midnight(start_day - timedelta(days=7), tz)
        previous_end = start
    elif key == "this_month":
        start_day = today.replace(day=1)
        end_day = _next_month(start_day)
        start = _midnight(start_day, tz)
        end = _midnight(end_day, tz)
        previous_start = _midnight(_previous_month(start_day), tz)
        previous_end = start
    elif key == "last_month":
        start_day = _previous_month(today.replace(day=1))
        end_day = today.replace(day=1)
        start = _midnight(start_day, tz)
        end = _midnight(end_day, tz)
        previous_start = _midnight(_previous_month(start_day), tz)
        previous_end = start
    elif key == "last_7_days":
        start_day = today - timedelta(days=6)
        start = _midnight(start_day, tz)
        end = _midnight(today + timedelta(days=1), tz)
        previous_end = start
        previous_start = start - timedelta(days=7)
    elif key == "last_30_days":
        start_day = today - timedelta(days=29)
        start = _midnight(start_day, tz)
        end = _midnight(today + timedelta(days=1), tz)
        previous_end = start
        previous_start = start - timedelta(days=30)
    elif key == "this_year":
        start_day = date(today.year, 1, 1)
        end_day = date(today.year + 1, 1, 1)
        start = _midnight(start_day, tz)
        end = _midnight(end_day, tz)
        previous_start = _midnight(date(today.year - 1, 1, 1), tz)
        previous_end = start
    elif key == "custom":
        if date_from is None or date_to is None:
            raise AppError("VALIDATION_ERROR", "Tanggal awal dan akhir wajib diisi.")
        if date_from > date_to:
            raise AppError("VALIDATION_ERROR", "Tanggal awal tidak boleh setelah tanggal akhir.")
        if (date_to - date_from).days > 366 * 5:
            raise AppError("VALIDATION_ERROR", "Rentang tanggal maksimal 5 tahun.")
        start = _midnight(date_from, tz)
        end = _midnight(date_to + timedelta(days=1), tz)
        span = end - start
        previous_end = start
        previous_start = start - span
    else:
        raise AppError(
            "VALIDATION_ERROR",
            f"Periode tidak dikenal: {key}",
            details={"allowed": list(PERIOD_KEYS)},
        )

    return PeriodRange(
        key=key,
        start=start.astimezone(timezone.utc),
        end=end.astimezone(timezone.utc),
        previous_start=previous_start.astimezone(timezone.utc),
        previous_end=previous_end.astimezone(timezone.utc),
        granularity=_granularity_for(start, end),
    )


def local_date(moment: datetime, tz: ZoneInfo) -> date:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(tz).date()


def bucket_start(day: date, granularity: Granularity) -> date:
    if granularity == "week":
        return day - timedelta(days=day.weekday())
    if granularity == "month":
        return day.replace(day=1)
    return day


def iter_buckets(start: datetime, end: datetime, tz: ZoneInfo, granularity: Granularity) -> list[date]:
    """Return every bucket start date covered by ``[start, end)``."""

    cursor = bucket_start(local_date(start, tz), granularity)
    last_day = local_date(end - timedelta(microseconds=1), tz)
    limit = bucket_start(last_day, granularity)

    buckets: list[date] = []
    while cursor <= limit:
        buckets.append(cursor)
        if granularity == "day":
            cursor += timedelta(days=1)
        elif granularity == "week":
            cursor += timedelta(days=7)
        else:
            cursor = _next_month(cursor)
    return buckets
