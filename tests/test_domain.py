from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tennis_booker.domain import (
    CourtOption,
    NoAvailableCourtError,
    NoReleaseWindowError,
    plan_release,
    select_preferred_court,
)

EASTERN = ZoneInfo("America/New_York")


def test_plans_next_release_when_started_ten_minutes_early():
    plan = plan_release(datetime(2026, 9, 5, 7, 50, tzinfo=EASTERN), range(8, 23))

    assert plan.release_at == datetime(2026, 9, 5, 8, tzinfo=EASTERN)
    assert plan.slot.reservation_date.isoformat() == "2026-09-07"
    assert plan.slot.hour == 8


def test_uses_same_release_during_hosted_runner_grace_period():
    plan = plan_release(datetime(2026, 9, 5, 8, 7, tzinfo=EASTERN), (8,))

    assert plan.release_at.hour == 8
    assert plan.slot.hour == 8


@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 9, 5, 7, 49, 59, tzinfo=EASTERN),
        datetime(2026, 9, 5, 8, 10, 1, tzinfo=EASTERN),
        datetime(2026, 9, 5, 22, 58, tzinfo=EASTERN),
    ],
)
def test_rejects_runs_outside_release_window(now):
    with pytest.raises(NoReleaseWindowError, match="release window"):
        plan_release(now, range(8, 23))


def test_requires_timezone_aware_clock():
    with pytest.raises(ValueError, match="timezone-aware"):
        plan_release(datetime(2026, 9, 5, 7, 58), (8,))


def test_selects_first_enabled_court_by_priority():
    options = (
        CourtOption("Court 3", "Court 3", enabled=False),
        CourtOption("Court 1", "Court 1"),
        CourtOption("Court 2", "Court 2"),
    )

    assert select_preferred_court(("Court 3", "Court 1"), options).label == "Court 1"


def test_falls_back_to_first_other_available_court():
    options = (
        CourtOption("---", "Unassigned"),
        CourtOption("Court 1", "Court 1", enabled=False),
        CourtOption("Court 4", "Court 4"),
        CourtOption("Court 5", "Court 5"),
    )

    assert select_preferred_court(("Court 1", "Court 2"), options).label == "Court 4"


def test_can_disable_fallback_to_unlisted_courts():
    with pytest.raises(NoAvailableCourtError, match="No acceptable court"):
        select_preferred_court(
            ("Court 1",),
            (CourtOption("Court 4", "Court 4"),),
            allow_any_available=False,
        )


def test_court_matching_ignores_case_and_repeated_whitespace():
    option = select_preferred_court(
        ("Court One",), (CourtOption("  COURT   ONE ", "Court One"),)
    )

    assert option.value == "Court One"


@pytest.mark.parametrize(
    "options",
    [
        (),
        (CourtOption("---", "Unassigned"),),
        (CourtOption("Court 1", "", True),),
    ],
)
def test_fails_when_no_real_court_is_selectable(options):
    with pytest.raises(NoAvailableCourtError, match="No acceptable court"):
        select_preferred_court(("Court 1",), options)
