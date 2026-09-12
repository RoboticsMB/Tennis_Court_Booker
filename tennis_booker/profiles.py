"""Booking profiles and weekly schedule parsing."""

from dataclasses import dataclass
import json
from typing import Iterable


DAY_NUMBERS = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}


class ProfileConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class BookingProfile:
    first_name: str
    last_name: str
    email: str
    hours_by_weekday: tuple[frozenset[int], ...]

    def matches(self, weekday: int, hour: int) -> bool:
        return hour in self.hours_by_weekday[weekday]

    @property
    def scheduled_hours(self) -> frozenset[int]:
        return frozenset().union(*self.hours_by_weekday)


def parse_profiles_json(raw: str) -> tuple[BookingProfile, ...]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProfileConfigurationError(f"Invalid booking profile JSON: {exc.msg}") from exc
    if not isinstance(data, list) or not data:
        raise ProfileConfigurationError("Booking profiles must be a non-empty JSON list")

    profiles = tuple(_parse_profile(item, index) for index, item in enumerate(data, 1))
    _reject_overlaps(profiles)
    return profiles


def profiles_for_slot(
    profiles: Iterable[BookingProfile], weekday: int, hour: int
) -> tuple[BookingProfile, ...]:
    return tuple(profile for profile in profiles if profile.matches(weekday, hour))


def all_scheduled_hours(profiles: Iterable[BookingProfile]) -> tuple[int, ...]:
    return tuple(sorted({hour for profile in profiles for hour in profile.scheduled_hours}))


def legacy_profile(
    first_name: str, last_name: str, email: str, hours: Iterable[int]
) -> BookingProfile:
    daily_hours = frozenset(hours)
    return BookingProfile(first_name, last_name, email, (daily_hours,) * 7)


def _parse_profile(item: object, index: int) -> BookingProfile:
    if not isinstance(item, dict):
        raise ProfileConfigurationError(f"Profile {index} must be a JSON object")
    identity = tuple(_text(item, field, index) for field in ("first_name", "last_name", "email"))
    schedule = item.get("schedule")
    if not isinstance(schedule, dict) or not schedule:
        raise ProfileConfigurationError(f"Profile {index} requires a non-empty schedule")

    days: list[set[int]] = [set() for _ in range(7)]
    for day_name, ranges in schedule.items():
        day = DAY_NUMBERS.get(str(day_name).strip().lower())
        if day is None:
            raise ProfileConfigurationError(f"Profile {index} has unknown day {day_name!r}")
        if not isinstance(ranges, list) or not ranges:
            raise ProfileConfigurationError(
                f"Profile {index} schedule for {day_name!r} must be a non-empty list"
            )
        for time_range in ranges:
            days[day].update(_parse_range(time_range, index))
    return BookingProfile(*identity, tuple(frozenset(hours) for hours in days))


def _text(item: dict, field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ProfileConfigurationError(f"Profile {index} requires {field}")
    return value.strip()


def _parse_range(value: object, index: int) -> range:
    if not isinstance(value, str):
        raise ProfileConfigurationError(f"Profile {index} time ranges must be strings")
    try:
        start, end = (int(part.strip()) for part in value.split("-", 1))
    except (ValueError, TypeError) as exc:
        raise ProfileConfigurationError(
            f"Profile {index} range {value!r} must look like '16-20'"
        ) from exc
    if not 0 <= start < end <= 24:
        raise ProfileConfigurationError(
            f"Profile {index} range {value!r} must be ascending within 0-24"
        )
    return range(start, end)


def _reject_overlaps(profiles: tuple[BookingProfile, ...]) -> None:
    claimed: dict[tuple[int, int], str] = {}
    for profile in profiles:
        for day, hours in enumerate(profile.hours_by_weekday):
            for hour in hours:
                key = (day, hour)
                if owner := claimed.get(key):
                    raise ProfileConfigurationError(
                        f"Schedule overlap at weekday {day}, hour {hour}: "
                        f"{owner} and {profile.first_name} {profile.last_name}"
                    )
                claimed[key] = f"{profile.first_name} {profile.last_name}"
