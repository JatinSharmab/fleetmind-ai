from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.llm.contracts import (
    ModelSpec,
    ProviderName,
    ProviderResult,
    StructuredGenerationRequest,
)


TModel = TypeVar(
    "TModel",
    bound=BaseModel,
)


class ProviderAdapter(Protocol):
    """Interface every FleetMind model provider adapter must implement."""

    name: ProviderName

    async def generate_structured(
        self,
        *,
        model: ModelSpec,
        request: StructuredGenerationRequest,
        response_model: type[TModel],
    ) -> ProviderResult:
        ...

    async def close(self) -> None:
        ...