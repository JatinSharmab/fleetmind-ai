import asyncpg
from pydantic import SecretStr


class PostgresManager:
    """Lifecycle wrapper around the PostgreSQL connection pool."""

    def __init__(self, dsn: SecretStr) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is not None:
            return

        self._pool = await asyncpg.create_pool(
            dsn=self._dsn.get_secret_value(),
            min_size=1,
            max_size=5,
            command_timeout=5,
        )

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def ping(self) -> bool:
        if self._pool is None:
            return False

        try:
            async with self._pool.acquire() as connection:
                result = await connection.fetchval("SELECT 1")
                return result == 1
        except Exception:
            return False