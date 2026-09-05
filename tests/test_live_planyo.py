"""Opt-in, non-submitting compatibility test for the live UMD Planyo form."""

from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import sync_playwright

from tennis_booker.browser import ReservationDetails, navigate_to_form, populate_and_verify_form
from tennis_booker.domain import BookingSlot


ENTRY_URL = "https://recwell.umd.edu/facilities/court-reservations"


@pytest.mark.browser
@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_LIVE_E2E") != "1", reason="live test is opt-in")
def test_live_form_accepts_and_retains_dry_run_values_without_submitting():
    now = datetime.now(ZoneInfo("America/New_York"))
    target_date = (now + timedelta(days=2)).date()
    details = ReservationDetails(
        BookingSlot(target_date, now.hour),
        "Playwright",
        "DryRun",
        "playwright-test@umd.edu",
        tuple(f"Court {number}" for number in range(1, 9)),
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=100)
        try:
            page = browser.new_page()
            form = navigate_to_form(page, ENTRY_URL)
            original_url = page.url
            page.evaluate(
                """() => {
                    window.__submitAttempted = false;
                    document.addEventListener('submit', event => {
                        window.__submitAttempted = true;
                        event.preventDefault();
                    }, true);
                }"""
            )
            snapshot = populate_and_verify_form(form, details)
            page.wait_for_timeout(1000)

            assert page.title() == "University of Maryland Recreation & Wellness"
            assert snapshot.date_text == target_date.strftime("%B %d, %Y")
            assert snapshot.hour == str(now.hour)
            assert snapshot.court in details.preferred_courts
            assert snapshot.first_name == "Playwright"
            assert snapshot.last_name == "DryRun"
            assert snapshot.email == "playwright-test@umd.edu"
            assert page.url == original_url
            assert page.evaluate("window.__submitAttempted") is False
        finally:
            browser.close()
