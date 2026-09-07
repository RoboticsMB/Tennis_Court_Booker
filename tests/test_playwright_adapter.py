from datetime import date

import pytest
from playwright.sync_api import sync_playwright

from tennis_booker.browser import ReservationDetails, populate_and_verify_form
from tennis_booker.domain import BookingSlot


FORM_HTML = """
<main>
  <input class="with-status-border form-control" aria-label="Unrelated field">
  <input id="one_date" class="with-status-border form-control" aria-label="Date">
  <select id="start_time" class="with-status-border form-control" aria-label="Time">
    <option value="8">8:00 AM</option><option value="9">9:00 AM</option>
  </select>
  <select id="assignment1" class="with-status-border form-control" aria-label="Court">
    <option value="">Choose a court</option>
    <option value="court-three" disabled>Court 3</option>
    <option value="court-one">Court 1</option>
    <option value="court-two">Court 2</option>
    <option value="court-four">Court 4</option>
  </select>
  <input id="first" class="with-status-border form-control" aria-label="First name">
  <input id="last" class="with-status-border form-control" aria-label="Last name">
  <input id="email" class="with-status-border form-control" aria-label="Email">
  <input id="submit_button" type="submit" class="btn btn-primary btn-lg"
         onclick="window.submitted = true" value="Make reservation">
</main>
"""


@pytest.mark.browser
def test_headed_browser_populates_and_verifies_every_field_without_submitting():
    details = ReservationDetails(
        BookingSlot(date(2026, 9, 7), 9),
        "Ada",
        "Lovelace",
        "ada@example.test",
        ("Court 3", "Court 1", "Court 2"),
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=100)
        try:
            page = browser.new_page()
            page.set_content(FORM_HTML)
            page.eval_on_selector(
                "#start_time",
                """element => element.addEventListener('change', () => setTimeout(() => {
                    if (!window.courtResetOnce) {
                        document.querySelector('#assignment1').selectedIndex = 0;
                        window.courtResetOnce = true;
                    }
                }, 450))""",
            )
            snapshot = populate_and_verify_form(page.main_frame, details)
            page.wait_for_timeout(750)

            assert snapshot.date_text == "September 07, 2026"
            assert snapshot.hour == "9"
            assert snapshot.court == "Court 1"
            assert snapshot.first_name == "Ada"
            assert snapshot.last_name == "Lovelace"
            assert snapshot.email == "ada@example.test"
            assert page.evaluate("window.submitted === true") is False
        finally:
            browser.close()


@pytest.mark.browser
def test_headed_browser_falls_back_when_event_blocks_all_preferred_courts():
    details = ReservationDetails(
        BookingSlot(date(2026, 9, 7), 9),
        "Ada",
        "Lovelace",
        "ada@example.test",
        ("Court 1", "Court 2", "Court 3"),
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=100)
        try:
            page = browser.new_page()
            page.set_content(FORM_HTML)
            page.locator("#assignment1 option").evaluate_all(
                """options => options.forEach(option => {
                    if (['Court 1', 'Court 2', 'Court 3'].includes(option.textContent.trim()))
                        option.disabled = true;
                })"""
            )

            snapshot = populate_and_verify_form(page.main_frame, details)

            assert snapshot.court == "Court 4"
            assert page.evaluate("window.submitted === true") is False
        finally:
            browser.close()
