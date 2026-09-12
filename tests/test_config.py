import pytest

from tennis_booker.config import ConfigurationError, Settings

BASE_ENV = {"BOOKER_FIRST_NAME": "Ada", "BOOKER_LAST_NAME": "Lovelace", "BOOKER_EMAIL": "ada@example.com", "PREFERRED_COURTS": "Court 3, Court 1, Court 2"}


def test_loads_required_values_and_safe_defaults():
    settings = Settings.from_env(BASE_ENV)
    assert settings.profiles[0].first_name == "Ada"
    assert settings.profiles[0].matches(0, 8)
    assert settings.preferred_courts == ("Court 3", "Court 1", "Court 2")
    assert settings.reservation_hours == tuple(range(8, 23))
    assert settings.allow_any_available_court is True
    assert settings.booking_days_ahead == 2
    assert settings.timezone == "America/New_York"
    assert settings.release_lead_minutes == 10
    assert "recwell.umd.edu" in settings.entry_url
    assert settings.dry_run is False
    assert settings.headless is True


def test_accepts_explicit_hour_list_and_optional_values():
    env = {**BASE_ENV, "RESERVATION_HOURS": "8,12,22", "BOOKING_DAYS_AHEAD": "3", "RELEASE_LEAD_MINUTES": "4", "LATE_START_GRACE_MINUTES": "7", "ALLOW_ANY_AVAILABLE_COURT": "false", "DRY_RUN": "yes", "HEADLESS": "false", "FAILURE_WEBHOOK_URL": "https://example.test/failure"}
    settings = Settings.from_env(env)
    assert settings.reservation_hours == (8, 12, 22)
    assert settings.booking_days_ahead == 3
    assert settings.release_lead_minutes == 4
    assert settings.late_start_grace_minutes == 7
    assert settings.allow_any_available_court is False
    assert settings.dry_run is True
    assert settings.headless is False


@pytest.mark.parametrize("missing", BASE_ENV)
def test_rejects_missing_required_values(missing):
    env = {key: value for key, value in BASE_ENV.items() if key != missing}
    with pytest.raises(ConfigurationError, match=missing):
        Settings.from_env(env)


@pytest.mark.parametrize("hours", ["23-8", "24", "8,8", "eight"])
def test_rejects_invalid_hours(hours):
    with pytest.raises(ConfigurationError, match="RESERVATION_HOURS"):
        Settings.from_env({**BASE_ENV, "RESERVATION_HOURS": hours})


def test_rejects_invalid_boolean():
    with pytest.raises(ConfigurationError, match="DRY_RUN"):
        Settings.from_env({**BASE_ENV, "DRY_RUN": "sometimes"})


def test_rejects_negative_booking_horizon():
    with pytest.raises(ConfigurationError, match="BOOKING_DAYS_AHEAD"):
        Settings.from_env({**BASE_ENV, "BOOKING_DAYS_AHEAD": "-1"})


def test_rejects_unknown_timezone():
    with pytest.raises(ConfigurationError, match="RESERVATION_TIMEZONE"):
        Settings.from_env({**BASE_ENV, "RESERVATION_TIMEZONE": "Mars/Olympus"})


def test_loads_profiles_from_json_and_derives_union_of_hours():
    profiles = """[
      {"first_name":"A","last_name":"One","email":"a@example.com",
       "schedule":{"monday":["16-20"]}},
      {"first_name":"B","last_name":"Two","email":"b@example.com",
       "schedule":{"friday":["9-16","20-23"]}}
    ]"""
    settings = Settings.from_env(
        {"BOOKING_PROFILES_JSON": profiles, "PREFERRED_COURTS": "Court 8,Court 7"}
    )

    assert len(settings.profiles) == 2
    assert settings.reservation_hours == tuple(range(9, 23))


def test_loads_profiles_from_file(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(
        '[{"first_name":"A","last_name":"One","email":"a@example.com",'
        '"schedule":{"sunday":["10-12"]}}]',
        encoding="utf-8",
    )

    settings = Settings.from_env(
        {"BOOKING_PROFILES_FILE": str(path), "PREFERRED_COURTS": "Court 8"}
    )

    assert settings.profiles[0].matches(6, 10)
    assert settings.reservation_hours == (10, 11)


def test_rejects_both_profile_sources():
    with pytest.raises(ConfigurationError, match="not both"):
        Settings.from_env(
            {
                "BOOKING_PROFILES_JSON": "[]",
                "BOOKING_PROFILES_FILE": "profiles.json",
                "PREFERRED_COURTS": "Court 8",
            }
        )
