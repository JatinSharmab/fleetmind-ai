from redis.asyncio import Redis


class RedisManager:
    """Lifecycle wrapper around the asynchronous Redis client."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis has not been connected.")
        return self._client

    async def connect(self) -> None:
        if self._client is not None:
            return

        self._client = Redis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )

        await self._client.ping()

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ping(self) -> bool:
        if self._client is None:
            return False

        try:
            return bool(await self._client.ping())
        except Exception:
            return False