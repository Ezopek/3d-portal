"""arq worker package.

WorkerSettings class is the entry point for the arq CLI:

    arq app.workers.WorkerSettings

"""

from typing import ClassVar

from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.cleanup_refresh_tokens import cleanup_refresh_tokens
from app.workers.generate_thumbnail import generate_thumbnail

#: Dedicated queue name for api-arq-worker tasks (cleanup_refresh_tokens cron
#: + generate_thumbnail). Separate from the render-worker's default ``arq:queue``
#: so the two worker pools don't grab each other's jobs and reject them with
#: "function 'X' not found" (pre-existing bug pre-Init-8; surfaced loud by
#: Story 13.2 thumbnail backfill spam). Render worker (workers/render/render/
#: worker.py) keeps the default queue — its render_model enqueues from
#: apps/api/app/modules/sot/admin_service.py also default — so no render-side
#: change is required. All api-side enqueue_job callers MUST pass
#: ``_queue_name=API_QUEUE_NAME`` to land in this queue.
API_QUEUE_NAME = "arq:api"


class WorkerSettings:
    """arq worker configuration."""

    queue_name: ClassVar[str] = API_QUEUE_NAME
    functions: ClassVar[list] = [cleanup_refresh_tokens, generate_thumbnail]
    cron_jobs: ClassVar[list] = [
        cron(cleanup_refresh_tokens, hour={3}, minute={15}),  # 03:15 UTC daily
    ]
    # arq's create_pool reads `redis_settings` as a class attribute and accesses
    # `.host` on it directly. Wrapping it in @classmethod (the prior shape) made
    # the attribute resolve to a bound classmethod object, which has no .host
    # → arq-worker container stuck in restart loop. Match the working pattern
    # from workers/render/render/worker.py: bare class attribute, eager call.
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
