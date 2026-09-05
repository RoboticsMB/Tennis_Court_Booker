import json

import pytest

from tennis_booker.notification import notify_failure


class Response:
    def __init__(self, status=204):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass


def test_disabled_notification_does_not_make_request():
    assert notify_failure(None, "failed", opener=lambda *_args, **_kwargs: None) is False


def test_posts_failure_only_json_payload():
    captured = {}

    def opener(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    assert notify_failure("https://example.test/hook", "No court", opener=opener) is True
    assert captured["timeout"] == 10
    assert captured["request"].method == "POST"
    assert json.loads(captured["request"].data) == {
        "status": "failure",
        "message": "No court",
    }


def test_rejects_unsuccessful_webhook_response():
    with pytest.raises(RuntimeError, match="HTTP 500"):
        notify_failure("https://example.test/hook", "failed", opener=lambda *_a, **_k: Response(500))
