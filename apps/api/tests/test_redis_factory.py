import fakeredis.aioredis
import pytest

from app.core.redis import RedisFactory


@pytest.mark.asyncio
async def test_factory_returns_async_client():
    fake = fakeredis.aioredis.FakeRedis()
    factory = RedisFactory(client=fake)
    client = factory.get()
    await client.set("k", "v")
    assert await client.get("k") == b"v"
