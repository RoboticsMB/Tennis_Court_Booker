"""Failure-only webhook notifications."""

import json
from urllib.request import Request, urlopen


def notify_failure(webhook_url: str | None, message: str, opener=urlopen) -> bool:
    """Send a small JSON failure payload; return False when notifications are disabled."""
    if not webhook_url:
        return False
    payload = json.dumps({"status": "failure", "message": message}).encode("utf-8")
    request = Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener(request, timeout=10) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f"Failure webhook returned HTTP {response.status}")
    return True
