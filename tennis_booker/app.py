"""Application orchestration."""

from datetime import datetime
import logging
import os
from time import sleep
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from .browser import ReservationDetails, navigate_to_form, populate_and_verify_form, submit_form
from .config import Settings
from .domain import plan_release
from .notification import notify_failure

LOGGER = logging.getLogger(__name__)


def wait_until(release_at: datetime, clock=datetime.now, sleeper=sleep) -> None:
    """Wait with short sleeps so form entry begins on the release boundary."""
    while (remaining := (release_at - clock(release_at.tzinfo)).total_seconds()) > 0:
        sleeper(min(remaining, 0.25))


def run(settings: Settings) -> None:
    timezone = ZoneInfo(settings.timezone)
    plan = plan_release(
        datetime.now(timezone),
        settings.reservation_hours,
        days_ahead=settings.booking_days_ahead,
        lead_minutes=settings.release_lead_minutes,
        late_grace_minutes=settings.late_start_grace_minutes,
    )
    details = ReservationDetails(
        plan.slot,
        settings.first_name,
        settings.last_name,
        settings.email,
        settings.preferred_courts,
        settings.allow_any_available_court,
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=settings.headless)
        try:
            page = browser.new_page()
            form = navigate_to_form(page, settings.entry_url)
            wait_until(plan.release_at)
            populate_and_verify_form(form, details)
            if not settings.dry_run:
                submit_form(form)
        finally:
            browser.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        run(Settings.from_env())
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        LOGGER.error("Reservation failed: %s", message)
        try:
            notify_failure(os.getenv("FAILURE_WEBHOOK_URL"), message)
        except Exception as notification_error:
            LOGGER.error("Failure notification could not be delivered: %s", notification_error)
        raise SystemExit(1) from exc
