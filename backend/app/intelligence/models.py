from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.llm.contracts import (
    ModelCallMetadata,
    ProviderName,
)


EventCategory = Literal[
    "road.blocked",
    "traffic.increased",
    "customer.unavailable",
    "customer.changed_address",
    "battery.low",
    "charger.unavailable",
    "package.mismatch",
    "vehicle.warning",
    "weather.changed",
    "delivery.failed",
    "unknown",
]


EventUrgency = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


RecommendedCapability = Literal[
    "route",
    "customer",
    "energy",
    "delivery",
    "verification",
    "exception",
    "mission",
]


class EventUnderstandingRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    raw_event: str = Field(
        min_length=1,
        max_length=4000,
    )

    mission_id: str = Field(
        min_length=1
    )

    vehicle_id: str = Field(
        min_length=1
    )

    context: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict
    )

    preferred_provider: (
        ProviderName | None
    ) = None


class EventUnderstanding(BaseModel):
    """Strict output expected from the model."""

    model_config = ConfigDict(
        extra="forbid"
    )

    category: EventCategory

    urgency: EventUrgency

    affected_entity: str

    summary: str

    likely_impact: str

    recommended_capability: (
        RecommendedCapability
    )

    should_interrupt_current_mission: bool

    confidence: float = Field(
        ge=0,
        le=1,
    )

    facts: list[str]

    assumptions: list[str]


class EventUnderstandingResponse(BaseModel):
    understanding: EventUnderstanding
    model_call: ModelCallMetadata