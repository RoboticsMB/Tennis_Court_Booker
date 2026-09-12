import json

import pytest

from tennis_booker.profiles import (
    ProfileConfigurationError,
    all_scheduled_hours,
    legacy_profile,
    parse_profiles_json,
    profiles_for_slot,
)


def _profiles():
    return parse_profiles_json(
        json.dumps(
            [
                {
                    "first_name": "Person",
                    "last_name": "One",
                    "email": "one@example.com",
                    "schedule": {
                        "monday": ["16-20"],
                        "wednesday": ["16-20"],
                        "friday": ["16-20"],
                    },
                },
                {
                    "first_name": "Person",
                    "last_name": "Two",
                    "email": "two@example.com",
                    "schedule": {
                        "monday": ["22-24"],
                        "wednesday": ["22-24"],
                        "thursday": ["22-24"],
                        "friday": ["9-16", "20-23"],
                        "saturday": ["10-15"],
                        "sunday": ["10-15"],
                    },
                },
                {
                    "first_name": "Person",
                    "last_name": "Three",
                    "email": "three@example.com",
                    "schedule": {"saturday": ["15-22"], "sunday": ["15-22"]},
                },
            ]
        )
    )


def test_selects_person_for_weekday_and_hour_with_end_exclusive_ranges():
    profiles = _profiles()

    assert profiles_for_slot(profiles, 0, 19)[0].last_name == "One"
    assert profiles_for_slot(profiles, 0, 20) == ()
    assert profiles_for_slot(profiles, 0, 22)[0].last_name == "Two"
    assert profiles_for_slot(profiles, 0, 23)[0].last_name == "Two"
    assert profiles_for_slot(profiles, 0, 0) == ()


def test_weekend_handoff_is_non_overlapping():
    profiles = _profiles()

    assert profiles_for_slot(profiles, 5, 14)[0].last_name == "Two"
    assert profiles_for_slot(profiles, 5, 15)[0].last_name == "Three"
    assert profiles_for_slot(profiles, 5, 21)[0].last_name == "Three"
    assert profiles_for_slot(profiles, 5, 22) == ()


def test_collects_all_hours_needed_by_the_timer():
    assert all_scheduled_hours(_profiles()) == tuple(range(9, 24))


@pytest.mark.parametrize(
    "value, message",
    [
        ("not-json", "Invalid booking profile JSON"),
        ("[]", "non-empty JSON list"),
        ('[{"first_name":"A"}]', "requires last_name"),
        (
            '[{"first_name":"A","last_name":"B","email":"a@example.com",'
            '"schedule":{"funday":["8-9"]}}]',
            "unknown day",
        ),
        (
            '[{"first_name":"A","last_name":"B","email":"a@example.com",'
            '"schedule":{"monday":["10-10"]}}]',
            "ascending within 0-24",
        ),
    ],
)
def test_rejects_invalid_profile_configuration(value, message):
    with pytest.raises(ProfileConfigurationError, match=message):
        parse_profiles_json(value)


def test_rejects_overlapping_people():
    raw = """[
      {"first_name":"A","last_name":"One","email":"a@example.com",
       "schedule":{"monday":["8-10"]}},
      {"first_name":"B","last_name":"Two","email":"b@example.com",
       "schedule":{"monday":["9-11"]}}
    ]"""

    with pytest.raises(ProfileConfigurationError, match="Schedule overlap"):
        parse_profiles_json(raw)


def test_legacy_profile_applies_the_same_hours_every_day():
    profile = legacy_profile("A", "One", "a@example.com", [8, 9])

    assert all(profile.matches(day, 8) for day in range(7))
    assert not profile.matches(0, 10)
