import secrets
from datetime import datetime, timedelta, timezone

from redis.asyncio import Redis

from app.modules.share.models import ShareToken

_KEY_PREFIX = "share:token:"
_BY_MODEL = "share:by-model:"


class ShareService:
    def __init__(self, *, redis: Redis) -> None:
        self._redis = redis

    async def create(self, *, model_id: str, expires_in_hours: int, created_by: int) -> ShareToken:
        if expires_in_hours < 1:
            raise ValueError("expires_in_hours must be >= 1")
        token = secrets.token_urlsafe(24)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=expires_in_hours)
        record = ShareToken(
            token=token,
            model_id=model_id,
            expires_at=expires_at,
            created_by=created_by,
            created_at=now,
        )
        await self._redis.set(
            _KEY_PREFIX + token,
            record.model_dump_json(),
            ex=expires_in_hours * 3600,
        )
        await self._redis.sadd(_BY_MODEL + model_id, token)
        return record

    async def resolve(self, token: str) -> ShareToken | None:
        raw = await self._redis.get(_KEY_PREFIX + token)
        if raw is None:
            return None
        return ShareToken.model_validate_json(raw)

    async def revoke(self, token: str) -> None:
        record = await self.resolve(token)
        await self._redis.delete(_KEY_PREFIX + token)
        if record is not None:
            await self._redis.srem(_BY_MODEL + record.model_id, token)

    async def list_active(self) -> list[ShareToken]:
        keys = []
        async for key in self._redis.scan_iter(match=_KEY_PREFIX + "*"):
            keys.append(key)
        if not keys:
            return []
        values = await self._redis.mget(keys)
        return [ShareToken.model_validate_json(v) for v in values if v is not None]
