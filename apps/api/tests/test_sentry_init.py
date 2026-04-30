"""Test the Sentry init guard behavior."""

from unittest.mock import patch

from app.core.sentry import init_sentry


def test_init_sentry_noop_when_dsn_none() -> None:
    """A None DSN must not call sentry_sdk.init."""
    with patch("app.core.sentry.sentry_sdk.init") as mock_init:
        init_sentry(dsn=None, environment="test", release="0.0.0")
    mock_init.assert_not_called()


def test_init_sentry_noop_when_dsn_empty_string() -> None:
    """An empty-string DSN must not call sentry_sdk.init either."""
    with patch("app.core.sentry.sentry_sdk.init") as mock_init:
        init_sentry(dsn="", environment="test", release="0.0.0")
    mock_init.assert_not_called()


def test_init_sentry_calls_init_when_dsn_present() -> None:
    """A valid DSN must call sentry_sdk.init with the expected kwargs."""
    with (
        patch("app.core.sentry.sentry_sdk.init") as mock_init,
        patch("app.core.sentry.sentry_sdk.set_tag") as mock_set_tag,
    ):
        init_sentry(
            dsn="https://key@example.test/1",
            environment="production",
            release="0.1.0",
        )
    mock_init.assert_called_once()
    kwargs = mock_init.call_args.kwargs
    assert kwargs["dsn"] == "https://key@example.test/1"
    assert kwargs["environment"] == "production"
    assert kwargs["release"] == "0.1.0"
    assert kwargs["traces_sample_rate"] == 0.0
    assert callable(kwargs["before_send"])
    mock_set_tag.assert_called_once_with("service", "api")
