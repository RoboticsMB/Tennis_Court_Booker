"""Validated environment configuration."""

from dataclasses import dataclass
import os
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigurationError(ValueError):
    pass


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value


def _integer(env: Mapping[str, str], name: str, default: int, minimum: int = 0) -> int:
    raw = env.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return value


def _boolean(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false, got {raw!r}")


def _csv(env: Mapping[str, str], name: str) -> tuple[str, ...]:
    values = tuple(part.strip() for part in env.get(name, "").split(",") if part.strip())
    if not values:
        raise ConfigurationError(f"{name} must contain at least one value")
    return values


def _hours(env: Mapping[str, str]) -> tuple[int, ...]:
    raw = env.get("RESERVATION_HOURS", "8-22").strip()
    try:
        if "-" in raw and "," not in raw:
            start, end = (int(part) for part in raw.split("-", 1))
            hours = tuple(range(start, end + 1)) if start <= end else ()
        else:
            hours = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    except ValueError as exc:
        raise ConfigurationError(
            "RESERVATION_HOURS must be an inclusive range (8-22) or list (8,10,14)"
        ) from exc
    if not hours or any(hour not in range(24) for hour in hours) or len(set(hours)) != len(hours):
        raise ConfigurationError("RESERVATION_HOURS must contain unique hours from 0 through 23")
    return hours


def _timezone(env: Mapping[str, str]) -> str:
    name = env.get("RESERVATION_TIMEZONE", "America/New_York").strip()
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ConfigurationError(f"Unknown RESERVATION_TIMEZONE: {name!r}") from exc
    return name


@dataclass(frozen=True)
class Settings:
    first_name: str
    last_name: str
    email: str
    preferred_courts: tuple[str, ...]
    reservation_hours: tuple[int, ...]
    entry_url: str = "https://recwell.umd.edu/facilities/court-reservations"
    timezone: str = "America/New_York"
    booking_days_ahead: int = 2
    release_lead_minutes: int = 10
    late_start_grace_minutes: int = 10
    notification_webhook_url: str | None = None
    dry_run: bool = False
    headless: bool = True

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        source = os.environ if env is None else env
        return cls(
            first_name=_required(source, "BOOKER_FIRST_NAME"),
            last_name=_required(source, "BOOKER_LAST_NAME"),
            email=_required(source, "BOOKER_EMAIL"),
            preferred_courts=_csv(source, "PREFERRED_COURTS"),
            reservation_hours=_hours(source),
            entry_url=source.get("RESERVATION_ENTRY_URL", cls.entry_url).strip(),
            timezone=_timezone(source),
            booking_days_ahead=_integer(source, "BOOKING_DAYS_AHEAD", 2),
            release_lead_minutes=_integer(source, "RELEASE_LEAD_MINUTES", 10),
            late_start_grace_minutes=_integer(source, "LATE_START_GRACE_MINUTES", 10),
            notification_webhook_url=source.get("FAILURE_WEBHOOK_URL") or None,
            dry_run=_boolean(source, "DRY_RUN", False),
            headless=_boolean(source, "HEADLESS", True),
        )
