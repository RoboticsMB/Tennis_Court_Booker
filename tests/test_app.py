from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from tennis_booker.app import wait_until
from tennis_booker import app
from tennis_booker.config import Settings
from tennis_booker.profiles import legacy_profile


def test_wait_until_reaches_release_boundary_with_short_sleeps():
    timezone = ZoneInfo("America/New_York")
    current = [datetime(2026, 9, 5, 7, 59, 59, 400000, tzinfo=timezone)]
    release = datetime(2026, 9, 5, 8, tzinfo=timezone)
    sleeps = []

    def clock(_timezone):
        return current[0]

    def sleeper(seconds):
        sleeps.append(seconds)
        current[0] += timedelta(seconds=seconds)

    wait_until(release, clock=clock, sleeper=sleeper)

    assert current[0] == release
    assert sleeps == pytest.approx([0.25, 0.25, 0.1])


def test_main_notifies_only_after_failure(monkeypatch):
    settings = object()
    notifications = []
    monkeypatch.setattr(app.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(app, "run", lambda _settings: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(app, "notify_failure", lambda url, message: notifications.append((url, message)))
    monkeypatch.setenv("FAILURE_WEBHOOK_URL", "https://example.test/hook")

    with pytest.raises(SystemExit) as exit_info:
        app.main()

    assert exit_info.value.code == 1
    assert notifications == [("https://example.test/hook", "RuntimeError: boom")]


def test_main_emits_no_success_notification(monkeypatch):
    monkeypatch.setattr(app.Settings, "from_env", lambda: object())
    monkeypatch.setattr(app, "run", lambda _settings: None)
    monkeypatch.setattr(
        app, "notify_failure", lambda *_args: pytest.fail("success must not notify")
    )

    app.main()


def test_run_skips_browser_when_no_profile_matches_target_slot(monkeypatch):
    timezone = ZoneInfo("America/New_York")
    plan = app.plan_release(
        datetime(2026, 9, 6, 7, 50, tzinfo=timezone),
        [8],
        days_ahead=2,
        lead_minutes=10,
    )
    settings = Settings(
        profiles=(legacy_profile("A", "One", "a@example.com", [9]),),
        preferred_courts=("Court 8",),
        reservation_hours=(8,),
    )
    monkeypatch.setattr(app, "plan_release", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(
        app,
        "sync_playwright",
        lambda: pytest.fail("a browser must not start when nobody is scheduled"),
    )

    app.run(settings)
