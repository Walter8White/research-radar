from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from time import struct_time, mktime
from typing import Optional, Union


DEFAULT_RECENCY_DAYS = 7

RECENCY_OPTIONS = {
    "Last 24h": 1,
    "Last 3 days": 3,
    "Last 7 days": 7,
    "Last 30 days": 30,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_datetime(value: Union[str, datetime, struct_time, None]) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, struct_time):
        dt = datetime.fromtimestamp(mktime(value), tz=timezone.utc)
    else:
        text = str(value).strip()
        if not text:
            return None

        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = parsedate_to_datetime(text)
            except (TypeError, ValueError, IndexError, OverflowError):
                return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def normalize_datetime_string(value: Union[str, datetime, struct_time, None]) -> str:
    dt = normalize_datetime(value)
    return dt.isoformat() if dt else ""


def age_in_days(value: Union[str, datetime, struct_time, None]) -> Optional[int]:
    dt = normalize_datetime(value)
    if not dt:
        return None

    age = utc_now() - dt
    return max(0, age.days)


def is_recent(value: Union[str, datetime, struct_time, None], max_age_days: int) -> bool:
    dt = normalize_datetime(value)
    if not dt:
        return True

    return utc_now() - dt <= timedelta(days=max_age_days)


def freshness_score(value: Union[str, datetime, struct_time, None], max_age_days: int) -> float:
    dt = normalize_datetime(value)

    if not dt:
        return 15.0

    age_days = (utc_now() - dt).total_seconds() / 86400

    if age_days <= 1:
        return 100.0
    if age_days <= 3:
        return 85.0
    if age_days <= 7:
        return 70.0
    if age_days <= max_age_days:
        return 45.0

    return 10.0


def apply_freshness_adjustment(base_score: float, published_at: str, max_age_days: int) -> float:
    freshness = freshness_score(published_at, max_age_days)
    adjusted = base_score + ((freshness - 70.0) * 0.15)
    return max(0, min(adjusted, 95))


def format_date_with_age(value: Union[str, datetime, struct_time, None]) -> str:
    dt = normalize_datetime(value)

    if not dt:
        return "Unknown"

    age = age_in_days(dt)
    if dt.date() == utc_now().date():
        age_text = "today"
    elif age == 1:
        age_text = "1 day ago"
    elif age == 0:
        age_text = "less than 1 day ago"
    else:
        age_text = f"{age} days ago"

    return f"{dt.date().isoformat()} ({age_text})"
