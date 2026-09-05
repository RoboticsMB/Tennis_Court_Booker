"""Pure scheduling and court-selection rules."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re
from typing import Iterable


class BookingError(RuntimeError):
    pass


class NoReleaseWindowError(BookingError):
    pass


class NoAvailableCourtError(BookingError):
    pass


@dataclass(frozen=True)
class BookingSlot:
    reservation_date: date
    hour: int


@dataclass(frozen=True)
class ReleasePlan:
    release_at: datetime
    slot: BookingSlot


@dataclass(frozen=True)
class CourtOption:
    label: str
    value: str
    enabled: bool = True


def plan_release(
    now: datetime,
    reservation_hours: Iterable[int],
    *,
    days_ahead: int = 2,
    lead_minutes: int = 10,
    late_grace_minutes: int = 10,
) -> ReleasePlan:
    """Choose the current or next hour boundary without selecting the wrong slot."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    allowed = frozenset(reservation_hours)
    current_boundary = now.replace(minute=0, second=0, microsecond=0)
    for release_at in (current_boundary, current_boundary + timedelta(hours=1)):
        offset = (release_at - now).total_seconds()
        if (
            release_at.hour in allowed
            and -late_grace_minutes * 60 <= offset <= lead_minutes * 60
        ):
            return ReleasePlan(
                release_at=release_at,
                slot=BookingSlot((release_at + timedelta(days=days_ahead)).date(), release_at.hour),
            )
    raise NoReleaseWindowError("Run is outside the configured release window")


def select_preferred_court(
    preferred_courts: Iterable[str], options: Iterable[CourtOption]
) -> CourtOption:
    available = {
        _normalize(option.label): option
        for option in options
        if option.enabled and option.value.strip()
    }
    for preference in preferred_courts:
        if match := available.get(_normalize(preference)):
            return match
    raise NoAvailableCourtError("None of the preferred courts are selectable")


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
