from redis.asyncio import Redis


class RedisFactory:
    def __init__(self, *, client: Redis | None = None, url: str | None = None) -> None:
        if client is not None:
            self._client = client
        elif url is not None:
            self._client = Redis.from_url(url, decode_responses=False)
        else:
            raise ValueError("Provide client or url")

    def get(self) -> Redis:
        return self._client

    async def aclose(self) -> None:
        await self._client.aclose()
