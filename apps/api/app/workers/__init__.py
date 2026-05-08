"""arq worker package.

WorkerSettings class is the entry point for the arq CLI:

    arq app.workers.WorkerSettings

"""
from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.cleanup_refresh_tokens import cleanup_refresh_tokens


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    """arq worker configuration."""

    functions = [cleanup_refresh_tokens]
    cron_jobs = [
        cron(cleanup_refresh_tokens, hour={3}, minute={15}),  # 03:15 UTC daily
    ]

    @classmethod
    def redis_settings(cls) -> RedisSettings:
        return _redis_settings()
