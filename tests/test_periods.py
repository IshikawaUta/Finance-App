from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from finance_app.errors import AppError
from finance_app.periods import iter_buckets, resolve_period

JAKARTA = ZoneInfo("Asia/Jakarta")
UTC = ZoneInfo("UTC")
NOW = datetime(2026, 10, 24, 12, 30, tzinfo=JAKARTA)


def local_date(moment: datetime) -> date:
    return moment.astimezone(JAKARTA).date()


def test_this_month_is_half_open_in_utc() -> None:
    period = resolve_period("this_month", tz=JAKARTA, now=NOW)

    assert period.start == datetime(2026, 9, 30, 17, 0, tzinfo=UTC)
    assert period.end == datetime(2026, 10, 31, 17, 0, tzinfo=UTC)
    assert local_date(period.start) == date(2026, 10, 1)
    assert local_date(period.end) == date(2026, 11, 1)
    assert period.granularity == "day"


def test_last_month_previous_period_is_month_before() -> None:
    period = resolve_period("last_month", tz=JAKARTA, now=NOW)

    assert local_date(period.start) == date(2026, 9, 1)
    assert local_date(period.end) == date(2026, 10, 1)
    assert local_date(period.previous_start) == date(2026, 8, 1)
    assert period.previous_end == period.start


def test_this_week_starts_on_monday() -> None:
    period = resolve_period("this_week", tz=JAKARTA, now=NOW)

    assert local_date(period.start) == date(2026, 10, 19)
    assert local_date(period.end) == date(2026, 10, 26)


def test_last_7_days_includes_today() -> None:
    period = resolve_period("last_7_days", tz=JAKARTA, now=NOW)

    assert local_date(period.start) == date(2026, 10, 18)
    assert local_date(period.end) == date(2026, 10, 25)


def test_custom_range_is_inclusive() -> None:
    period = resolve_period(
        "custom",
        tz=JAKARTA,
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 3),
        now=NOW,
    )

    assert local_date(period.start) == date(2026, 10, 1)
    assert local_date(period.end) == date(2026, 10, 4)


def test_custom_range_requires_dates_and_valid_order() -> None:
    with pytest.raises(AppError):
        resolve_period("custom", tz=JAKARTA, date_from=date(2026, 10, 1), now=NOW)
    with pytest.raises(AppError):
        resolve_period(
            "custom",
            tz=JAKARTA,
            date_from=date(2026, 10, 3),
            date_to=date(2026, 10, 1),
            now=NOW,
        )


def test_unknown_period_is_rejected() -> None:
    with pytest.raises(AppError):
        resolve_period("decade", tz=JAKARTA, now=NOW)


def test_iter_buckets_fills_every_day() -> None:
    period = resolve_period("this_month", tz=JAKARTA, now=NOW)
    buckets = iter_buckets(period.start, period.end, JAKARTA, "day")

    assert len(buckets) == 31
    assert buckets[0] == date(2026, 10, 1)
    assert buckets[-1] == date(2026, 10, 31)


def test_iter_buckets_weekly_starts_monday() -> None:
    period = resolve_period("last_30_days", tz=JAKARTA, now=NOW)
    buckets = iter_buckets(period.start, period.end, JAKARTA, "week")

    assert all(day.weekday() == 0 for day in buckets)
    assert buckets[0] == date(2026, 9, 21)
    assert period.days == 30
    assert period.end - period.start == timedelta(days=30)
