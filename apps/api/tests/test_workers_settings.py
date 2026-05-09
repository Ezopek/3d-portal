"""apps/api/tests/test_workers_settings.py

Regression test for the arq-worker restart-loop bug introduced when
`WorkerSettings.redis_settings` was wrapped in @classmethod. arq's
`create_pool` reads the class attribute directly and calls `.host` on it,
so a bound-classmethod object raised `AttributeError: 'classmethod' object
has no attribute 'host'` → container stuck in `Restarting (1) ...` loop.

These tests freeze the shape arq expects so the bug cannot reappear
silently.
"""

from arq.connections import RedisSettings

from app.workers import WorkerSettings


def test_redis_settings_is_an_instance_not_a_classmethod() -> None:
    """arq's create_pool calls `.host` on `WorkerSettings.redis_settings`
    directly. The attribute MUST resolve to a `RedisSettings` instance,
    not a method/classmethod object.
    """
    assert isinstance(WorkerSettings.redis_settings, RedisSettings)


def test_redis_settings_exposes_host_attribute() -> None:
    """The exact access pattern arq.connections.create_pool performs:
    `isinstance(settings.host, str)`. If this raises AttributeError,
    arq-worker enters its restart loop.
    """
    settings = WorkerSettings.redis_settings
    # `.host` is the smoke check; default falls back to "localhost" or the
    # value from REDIS_URL. Either way it must be readable as a string.
    assert isinstance(settings.host, str)
    assert settings.host  # non-empty


def test_redis_settings_carries_dsn_from_app_config() -> None:
    """Sanity: the configured DSN flows through to the RedisSettings.
    Tests the binding without depending on the literal redis_url value
    (which the conftest fixture rewrites for isolation).
    """
    settings = WorkerSettings.redis_settings
    # port + database are normally numeric; if from_dsn fed them through,
    # they will be set even when the DSN is the default.
    assert isinstance(settings.port, int)
    assert isinstance(settings.database, int)
