# Tennis Court Booker

The application opens the public UMD RecWell court-reservations page, follows **Reserve a Tennis Court**, follows Planyo's **Make reservation**, waits for the exact release boundary, fills and verifies the form, and submits only when dry-run mode is disabled. It does not configure or construct Planyo calendar/resource IDs.

## Timing

Reservations open two days ahead at the matching local time. A process started at 7:50 a.m. plans the 8:00 a.m. release, prepares the browser, waits until 8:00, and requests the 8:00 a.m. slot two calendar days later. `RESERVATION_TIMEZONE` defaults to `America/New_York`, so daylight-saving changes require no cron edits.

The accepted start window defaults to ten minutes early through ten minutes late. A late runner targets the current release rather than silently switching hours, but no software can recover exact timing if the runner starts after the boundary. GitHub cron is not guaranteed to start precisely; a persistent host or self-hosted runner is preferable when second-level precision matters.

## Configuration

Use `.env.example` as a host/GitHub template. The application deliberately does not load `.env` files automatically.

Required:

- `BOOKER_FIRST_NAME`, `BOOKER_LAST_NAME`, `BOOKER_EMAIL`
- `PREFERRED_COURTS`, ordered from most to least preferred

`RESERVATION_HOURS` defaults to inclusive range `8-22` and also accepts a list such as `8,10,14,22`. `DRY_RUN=true` verifies without clicking. Production defaults to headless Chromium; set `HEADLESS=false` locally to watch it.

The application waits for Planyo's asynchronous court refresh, then chooses the first preferred selectable option. If all preferred courts are blocked by an event, `ALLOW_ANY_AVAILABLE_COURT=true` falls back to the first other selectable court. Set it to `false` to require a preferred court. Dropdown state cannot prove availability beyond what Planyo exposes.

`FAILURE_WEBHOOK_URL` is optional. Failures send one JSON POST with `status: failure` and an error message. Successful runs send no notification because Planyo handles confirmation email.

## Development and tests

Use Python 3.11:

```text
python -m pip install ".[test]"
python -m playwright install chromium
python -m pytest -m "not live"
```

The browser test uses `headless=False`; Linux CI supplies a display with `xvfb-run`. The live dry run uses synthetic data and a submit tripwire:

```text
RUN_LIVE_E2E=1 python -m pytest -m live -s
```

Run scheduled behavior after exporting configuration with `python -m tennis_booker`.

## Manual live submission

This command targets the current local hour two calendar days ahead, opens headed Chromium, fills and verifies your values, and pauses. It clicks **Make reservation** only after you type the displayed confirmation phrase.

```powershell
$env:BOOKER_FIRST_NAME = "Your first name"
$env:BOOKER_LAST_NAME = "Your last name"
$env:BOOKER_EMAIL = "you@umd.edu"
$env:PREFERRED_COURTS = "Court 1,Court 2,Court 3"
python -m tennis_booker.manual_submit
```

This can create a real reservation or trigger Planyo email verification. Anything except `SUBMIT LIVE RESERVATION` cancels safely. The command is separate from pytest and GitHub Actions, so automation cannot invoke it accidentally.

Keep secrets out of source control. Work in complete phases and run the full suite before continuing.
