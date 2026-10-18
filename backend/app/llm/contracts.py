from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class ProviderName(StrEnum):
    GROQ = "groq"
    GEMINI = "gemini"
    MISTRAL = "mistral"
    OLLAMA = "ollama"


class ModelTask(StrEnum):
    EVENT_UNDERSTANDING = "event_understanding"
    BASIC_REASONING = "basic_reasoning"


class ModelCapability(StrEnum):
    TEXT = "text"
    STRUCTURED_OUTPUT = "structured_output"
    REASONING = "reasoning"
    VISION = "vision"


class ModelSpec(BaseModel):
    """Static registry metadata about one available model."""

    model_config = ConfigDict(extra="forbid")

    key: str
    provider: ProviderName
    model_id: str

    capabilities: set[ModelCapability]
    tasks: set[ModelTask]

    priority: int = Field(ge=1)

    input_cost_per_million_usd: float | None = Field(default=None, ge=0)
    output_cost_per_million_usd: float | None = Field(default=None, ge=0)

    enabled: bool = True


class StructuredGenerationRequest(BaseModel):
    """Provider-independent request accepted by the Model Gateway."""

    model_config = ConfigDict(extra="forbid")

    task: ModelTask

    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)

    temperature: float = Field(default=0.0, ge=0, le=2)
    max_output_tokens: int = Field(default=512, ge=1, le=8192)

    timeout_seconds: float = Field(default=30.0, gt=0)

    preferred_provider: ProviderName | None = None


class ModelUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ProviderResult(BaseModel):
    """Normalized raw provider response before FleetMind validation."""

    model_config = ConfigDict(extra="forbid")

    text: str

    usage: ModelUsage = Field(default_factory=ModelUsage)

    finish_reason: str | None = None


class ModelCallMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderName
    model: str

    attempts: int = Field(ge=1)

    fallbacks: list[str]

    provider_latency_ms: float = Field(ge=0)
    total_latency_ms: float = Field(ge=0)

    usage: ModelUsage

    estimated_list_cost_usd: float | None = Field(default=None, ge=0)


TModel = TypeVar(
    "TModel",
    bound=BaseModel,
)


class GatewayResult(BaseModel, Generic[TModel]):
    model_config = ConfigDict(extra="forbid")

    output: TModel
    metadata: ModelCallMetadata