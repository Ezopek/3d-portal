"""arq worker package.

WorkerSettings class is the entry point for the arq CLI:

    arq app.workers.WorkerSettings

"""

from typing import ClassVar

from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.cleanup_refresh_tokens import cleanup_refresh_tokens


class WorkerSettings:
    """arq worker configuration."""

    functions: ClassVar[list] = [cleanup_refresh_tokens]
    cron_jobs: ClassVar[list] = [
        cron(cleanup_refresh_tokens, hour={3}, minute={15}),  # 03:15 UTC daily
    ]
    # arq's create_pool reads `redis_settings` as a class attribute and accesses
    # `.host` on it directly. Wrapping it in @classmethod (the prior shape) made
    # the attribute resolve to a bound classmethod object, which has no .host
    # → arq-worker container stuck in restart loop. Match the working pattern
    # from workers/render/render/worker.py: bare class attribute, eager call.
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
