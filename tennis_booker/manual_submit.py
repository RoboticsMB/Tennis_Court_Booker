"""Explicit, interactive live submission check. Never used by automation."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from .browser import ReservationDetails, navigate_to_form, populate_and_verify_form, submit_form
from .config import Settings
from .domain import BookingSlot

CONFIRMATION = "SUBMIT LIVE RESERVATION"


def main() -> None:
    settings = Settings.from_env()
    now = datetime.now(ZoneInfo(settings.timezone))
    if now.hour not in settings.reservation_hours:
        raise SystemExit(f"Current hour {now.hour} is not configured in RESERVATION_HOURS")
    slot = BookingSlot((now + timedelta(days=settings.booking_days_ahead)).date(), now.hour)
    details = ReservationDetails(
        slot,
        settings.first_name,
        settings.last_name,
        settings.email,
        settings.preferred_courts,
        settings.allow_any_available_court,
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=100)
        try:
            page = browser.new_page()
            form = navigate_to_form(page, settings.entry_url)
            snapshot = populate_and_verify_form(form, details)
            print(f"Ready to submit: {snapshot.date_text}, hour {snapshot.hour}, {snapshot.court}")
            print(f"Name: {snapshot.first_name} {snapshot.last_name}; email: {snapshot.email}")
            if input(f"Type {CONFIRMATION!r} to click Make reservation: ").strip() != CONFIRMATION:
                print("Cancelled; nothing was submitted.")
                return

            submit_form(form)
            page.wait_for_timeout(3000)
            if not page.locator("#submit_button").is_visible():
                print("Planyo accepted the form and advanced to the next step.")
            else:
                print("Planyo remained on the reservation form; inspect the visible validation message.")
                raise SystemExit(1)
            input("Press Enter to close the browser...")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
