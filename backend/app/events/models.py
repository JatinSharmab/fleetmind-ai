from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventType(StrEnum):
    MISSION_STARTED = "mission.started"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED = "mission.failed"

    VEHICLE_LOCATION_CHANGED = "vehicle.location_changed"
    BATTERY_LOW = "battery.low"

    DELIVERY_COMPLETED = "delivery.completed"


class FleetEvent(BaseModel):
    """Versioned event envelope used throughout FleetMind."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    schema_version: Literal["1.0"] = "1.0"

    source: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    mission_id: str
    vehicle_id: str

    correlation_id: UUID

    payload: dict[str, Any] = Field(default_factory=dict)