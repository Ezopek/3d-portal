"""Unit tests for ``TokenRedactionFilter`` (AC-4).

The filter wraps the API's structured-log pipeline so cleartext invite
tokens never reach stdout (and from there GlitchTip). Negative-path tests
guard against the filter mutating unrelated messages.
"""

from __future__ import annotations

import io
import json
import logging
import re

import pytest

from app.core.logging import JsonFormatter, TokenRedactionFilter, configure_logging


@pytest.fixture
def logger_to_buffer() -> tuple[logging.Logger, io.StringIO]:
    """Build an isolated logger emitting JSON-formatted records into a buffer."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.addFilter(TokenRedactionFilter())
    handler.setFormatter(
        JsonFormatter(
            service_name="3d-portal-api",
            service_version="test",
            environment="test",
        )
    )
    logger = logging.getLogger(f"test.{id(buf)}")
    logger.setLevel(logging.INFO)
    logger.handlers[:] = [handler]
    logger.propagate = False
    return logger, buf


def _make_record(msg: str, *args: object) -> logging.LogRecord:
    return logging.LogRecord(
        name="x",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=args or None,
        exc_info=None,
    )


def test_filter_redacts_token_in_url_query_string() -> None:
    record = _make_record("GET /register?token=abc123&utm=x")
    TokenRedactionFilter().filter(record)
    assert record.msg == "GET /register?token=<redacted>&utm=x"


def test_filter_redacts_token_in_extra_dict(
    logger_to_buffer: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, buf = logger_to_buffer
    logger.info("registered", extra={"token": "abc123"})
    line = buf.getvalue().strip()
    payload = json.loads(line)
    assert payload["message"] == "registered"
    # cleartext token must not appear anywhere in the rendered JSON
    assert "abc123" not in line


def test_filter_negative_path_no_token(
    logger_to_buffer: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, buf = logger_to_buffer
    logger.info("hello world")
    payload = json.loads(buf.getvalue().strip())
    assert payload["message"] == "hello world"


def test_filter_redacts_in_record_args(
    logger_to_buffer: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, buf = logger_to_buffer
    logger.info("query=%s logged", "token=abc123&foo=bar")
    line = buf.getvalue().strip()
    payload = json.loads(line)
    assert payload["message"] == "query=token=<redacted>&foo=bar logged"
    assert "abc123" not in line


def test_configure_logging_attaches_filter() -> None:
    configure_logging(
        service_name="3d-portal-api",
        service_version="test",
        environment="test",
    )
    root = logging.getLogger()
    assert root.handlers, "configure_logging must install a handler"
    handler = root.handlers[0]
    assert any(isinstance(f, TokenRedactionFilter) for f in handler.filters), (
        "TokenRedactionFilter must be attached before formatting"
    )


def test_filter_handles_non_string_msg() -> None:
    record = _make_record({"token": "abc"})  # type: ignore[arg-type]
    TokenRedactionFilter().filter(record)
    # str() coerces dict to its repr; redaction operates on the resulting text
    assert isinstance(record.msg, str)


def test_filter_strips_token_attribute_set_via_extra() -> None:
    record = _make_record("registered")
    record.token = "abc123"  # type: ignore[attr-defined]
    TokenRedactionFilter().filter(record)
    assert record.token == "<redacted>"  # type: ignore[attr-defined]


def test_filter_scan_no_cleartext_leakage(
    logger_to_buffer: tuple[logging.Logger, io.StringIO],
) -> None:
    """Defense-in-depth: nothing in any rendered line may contain a secret literal."""
    logger, buf = logger_to_buffer
    logger.info("GET /register?token=secretA&keep=ok")
    logger.info("registered", extra={"token": "secretB", "user_id": "u2"})
    logger.info("query=%s", "token=secretC&z=1")
    rendered = buf.getvalue()
    for needle in ("secretA", "secretB", "secretC"):
        assert not re.search(re.escape(needle), rendered), (
            f"cleartext {needle} leaked through redaction"
        )


def test_filter_redacts_url_original_passthrough(
    logger_to_buffer: tuple[logging.Logger, io.StringIO],
) -> None:
    """P1 regression — JsonFormatter pass-through keys must be redacted too.

    Without redacting record.__dict__ pass-through values, ``url.original``
    (or any other formatter-surfaced field) can leak a cleartext token.
    """
    logger, buf = logger_to_buffer
    logger.info(
        "registered",
        extra={"url.original": "/register?token=secret123&utm=x", "user_id": "u1"},
    )
    line = buf.getvalue().strip()
    payload = json.loads(line)
    assert "secret123" not in line
    assert payload["url.original"] == "/register?token=<redacted>&utm=x"
    # Unrelated extras must survive untouched.
    assert payload.get("user_id", "u1") == "u1"


def test_filter_redacts_event_prefixed_passthrough() -> None:
    """P1 regression — ``event.*`` keys are also formatter pass-through.

    The stdlib logger refuses dotted keys in ``extra=`` (raises ``KeyError``
    on reserved attribute names), so structured ``event.*`` fields are set
    directly on ``record.__dict__`` by middleware. We simulate that path
    here and assert the filter redacts cleartext tokens before the formatter
    surfaces the field on stdout.
    """
    record = logging.LogRecord(
        name="x",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="audit",
        args=None,
        exc_info=None,
    )
    record.__dict__["event.action"] = "redeem token=secretEvt&kind=admin"
    TokenRedactionFilter().filter(record)
    assert record.__dict__["event.action"] == "redeem token=<redacted>&kind=admin"


def test_filter_redacts_lazy_format_without_typeerror(
    logger_to_buffer: tuple[logging.Logger, io.StringIO],
) -> None:
    """P2 regression — lazy %s formatting must not desync record.msg vs record.args.

    Pre-fix behaviour: the filter substituted record.msg (removing the ``%s``
    placeholder) but left record.args intact. ``record.getMessage()`` then
    raised ``TypeError: not all arguments converted during string formatting``
    and the record was dropped.
    """
    logger, buf = logger_to_buffer
    # Two flavours: token IN the format string with %s for value, and
    # token IN the %s argument with no token in the format string.
    logger.info("GET /register?token=%s&foo=bar", "abc123")
    logger.info("token=%s logged", "secretXYZ")
    rendered = buf.getvalue()
    lines = [json.loads(ln) for ln in rendered.strip().splitlines()]
    assert len(lines) == 2, f"expected 2 records, got {len(lines)}: {rendered!r}"
    assert lines[0]["message"] == "GET /register?token=<redacted>&foo=bar"
    assert lines[1]["message"] == "token=<redacted> logged"
    assert "abc123" not in rendered
    assert "secretXYZ" not in rendered
