"""Playwright navigation and form interactions."""

from dataclasses import dataclass
import re

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .domain import BookingSlot, CourtOption, NoAvailableCourtError, select_preferred_court


class FormVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReservationDetails:
    slot: BookingSlot
    first_name: str
    last_name: str
    email: str
    preferred_courts: tuple[str, ...]
    allow_any_available_court: bool = True

    @property
    def date_text(self) -> str:
        return self.slot.reservation_date.strftime("%B %d, %Y")


@dataclass(frozen=True)
class FormSnapshot:
    date_text: str
    hour: str
    court: str
    first_name: str
    last_name: str
    email: str


def navigate_to_form(page, entry_url: str):
    page.goto(entry_url, wait_until="domcontentloaded", timeout=30000)
    _follow_link(page, "Reserve a Tennis Court")
    reservation_link = page.get_by_role(
        "link", name=re.compile(r"Make (?:a )?reservation", re.IGNORECASE)
    ).or_(page.locator('a[href*="mode=reserve"]')).first
    _follow_locator(page, reservation_link, "Make reservation")
    page.locator("#one_date").wait_for(timeout=10000)
    return page.main_frame


def _follow_link(page, name: str) -> None:
    """Follow a named site link without hard-coding its destination URL."""
    _follow_locator(page, page.get_by_role("link", name=name, exact=True), name)


def _follow_locator(page, link, description: str) -> None:
    try:
        link.wait_for(timeout=10000)
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(
            f"Link {description!r} was not found on {page.url!r} ({page.title()!r})"
        ) from exc
    destination = link.evaluate("element => element.href")
    page.goto(destination, wait_until="domcontentloaded", timeout=30000)


def populate_and_verify_form(frame, details: ReservationDetails) -> FormSnapshot:
    fields = {
        "date": frame.locator("#one_date"),
        "time": frame.locator("#start_time"),
        "court": frame.locator("#assignment1"),
        "first": frame.locator("#first"),
        "last": frame.locator("#last"),
        "email": frame.locator("#email"),
    }
    fields["date"].fill(details.date_text)
    fields["date"].dispatch_event("change")
    fields["time"].select_option(str(details.slot.hour))
    fields["first"].fill(details.first_name)
    fields["last"].fill(details.last_name)
    fields["email"].fill(details.email)

    court = _select_court_after_refresh(
        frame,
        fields["court"],
        details.preferred_courts,
        details.allow_any_available_court,
    )

    snapshot = FormSnapshot(
        fields["date"].input_value(),
        fields["time"].input_value(),
        fields["court"].locator("option:checked").inner_text().strip(),
        fields["first"].input_value(),
        fields["last"].input_value(),
        fields["email"].input_value(),
    )
    expected = FormSnapshot(
        details.date_text,
        str(details.slot.hour),
        court.label.strip(),
        details.first_name,
        details.last_name,
        details.email,
    )
    if snapshot != expected:
        raise FormVerificationError(
            f"Form verification failed: expected={expected!r}, actual={snapshot!r}"
        )
    return snapshot


def _select_court_after_refresh(
    frame,
    select,
    preferences: tuple[str, ...],
    allow_any_available: bool,
) -> CourtOption:
    for _attempt in range(3):
        try:
            frame.wait_for_function(
                """() => [...document.querySelectorAll('#assignment1 option')]
                    .some(option => option.value && option.value.toLowerCase() !== 'unassigned'
                        && option.textContent.trim() !== '---' && !option.disabled)""",
                timeout=10000,
            )
        except PlaywrightTimeoutError as exc:
            raise NoAvailableCourtError(
                "No court became selectable after Planyo refreshed availability"
            ) from exc

        court = select_preferred_court(
            preferences,
            (
                CourtOption(
                    option.inner_text(),
                    option.get_attribute("value") or "",
                    not option.is_disabled(),
                )
                for option in select.locator("option").all()
            ),
            allow_any_available=allow_any_available,
        )
        select.select_option(value=court.value)
        frame.wait_for_timeout(400)
        if select.input_value() == court.value:
            return court
    raise FormVerificationError("Planyo repeatedly reset the selected court after refresh")


def submit_form(frame) -> None:
    frame.locator("#submit_button").click()
