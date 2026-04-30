"""Tests for the Sentry before_send scrubber."""

from app.core.sentry import scrub_event


def test_scrubs_password_in_request_data() -> None:
    event = {"request": {"data": {"email": "a@b.c", "password": "hunter2"}}}
    result = scrub_event(event, hint={})
    assert result["request"]["data"]["password"] == "[Filtered]"
    assert result["request"]["data"]["email"] == "a@b.c"


def test_scrubs_authorization_header_case_insensitive() -> None:
    event = {"request": {"headers": {"Authorization": "Bearer xyz", "x-trace": "ok"}}}
    result = scrub_event(event, hint={})
    assert result["request"]["headers"]["Authorization"] == "[Filtered]"
    assert result["request"]["headers"]["x-trace"] == "ok"


def test_scrubs_cookie_header() -> None:
    event = {"request": {"headers": {"cookie": "session=abc"}}}
    result = scrub_event(event, hint={})
    assert result["request"]["headers"]["cookie"] == "[Filtered]"


def test_scrubs_token_keys_in_extra() -> None:
    event = {"extra": {"access_token": "AT", "refresh_token": "RT", "user_id": 7}}
    result = scrub_event(event, hint={})
    assert result["extra"]["access_token"] == "[Filtered]"
    assert result["extra"]["refresh_token"] == "[Filtered]"
    assert result["extra"]["user_id"] == 7


def test_scrubs_nested_dicts() -> None:
    event = {"extra": {"nested": {"password": "pw", "ok": "keep"}}}
    result = scrub_event(event, hint={})
    assert result["extra"]["nested"]["password"] == "[Filtered]"
    assert result["extra"]["nested"]["ok"] == "keep"


def test_returns_event_unchanged_when_no_sensitive_keys() -> None:
    event = {"request": {"data": {"q": "hello"}}, "extra": {"trace_id": "t-1"}}
    result = scrub_event(event, hint={})
    assert result == event


def test_handles_none_event() -> None:
    assert scrub_event(None, hint={}) is None
