"""Environment configuration and India Standard Time helpers."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
IST = timezone(timedelta(hours=5, minutes=30), name="IST")
UTC = timezone.utc
DAILY_EPOCH_DATE = date(2026, 11, 24)
DAILY_BOSS_COUNT = 5


def data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "./local_data")).expanduser().resolve()


def database_path() -> Path:
    return data_dir() / "bhavtaal.db"


def app_name() -> str:
    return os.environ.get("APP_NAME", "bhavtaal")


def port() -> int:
    try:
        return int(os.environ.get("PORT", "8000"))
    except ValueError:
        return 8000


def now_ist() -> datetime:
    return datetime.now(UTC).astimezone(IST)


def ist_date(value: datetime | date | None = None) -> date:
    if value is None:
        return now_ist().date()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(IST).date()
    return value


def daily_pool_index(pool_size: int, value: datetime | date | None = None) -> int:
    if pool_size <= 0:
        raise ValueError("pool_size must be positive")
    return (ist_date(value) - DAILY_EPOCH_DATE).days % pool_size


def daily_boss_index(value: datetime | date | None = None) -> int:
    return daily_pool_index(DAILY_BOSS_COUNT, value)


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def ist_timestamp(value: datetime | None = None) -> str:
    current = (value or datetime.now(UTC)).astimezone(IST)
    return current.isoformat(timespec="seconds")


def format_indian_rupees(value: int) -> str:
    """Format an integer amount with Indian digit grouping and the rupee sign."""
    number = int(value)
    sign = "-" if number < 0 else ""
    digits = str(abs(number))
    if len(digits) <= 3:
        grouped = digits
    else:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while head:
            groups.insert(0, head[-2:])
            head = head[:-2]
        grouped = ",".join([*groups, tail])
    return f"{sign}₹{grouped}"
