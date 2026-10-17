from typing import Protocol

from redis.asyncio import Redis

from app.events.models import FleetEvent


class EventPublisher(Protocol):
    async def publish(self, event: FleetEvent) -> str:
        """Publish an event and return the transport-generated identifier."""
        ...


class InMemoryEventPublisher:
    """Used by unit tests and standalone simulator demos."""

    def __init__(self) -> None:
        self.events: list[FleetEvent] = []

    async def publish(self, event: FleetEvent) -> str:
        self.events.append(event)
        return str(event.event_id)


class RedisEventPublisher:
    """Publishes FleetMind events into a Redis Stream."""

    def __init__(
        self,
        redis_client: Redis,
        stream_name: str,
    ) -> None:
        self._redis = redis_client
        self._stream_name = stream_name

    async def publish(self, event: FleetEvent) -> str:
        stream_id = await self._redis.xadd(
            self._stream_name,
            {"event": event.model_dump_json()},
            maxlen=10_000,
            approximate=True,
        )

        return str(stream_id)