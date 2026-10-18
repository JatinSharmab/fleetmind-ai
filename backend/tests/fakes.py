from collections import deque
from typing import TypeVar

from pydantic import BaseModel

from app.llm.contracts import (
    ModelSpec,
    ModelUsage,
    ProviderName,
    ProviderResult,
    StructuredGenerationRequest,
)


TModel = TypeVar(
    "TModel",
    bound=BaseModel,
)


class FakeProviderAdapter:
    def __init__(
        self,
        *,
        name: ProviderName,
        responses: list[
            ProviderResult | Exception
        ],
    ) -> None:
        self.name = name

        self._responses = deque(
            responses
        )

        self.calls = 0

    async def generate_structured(
        self,
        *,
        model: ModelSpec,
        request: StructuredGenerationRequest,
        response_model: type[TModel],
    ) -> ProviderResult:
        del model
        del request
        del response_model

        self.calls += 1

        item = self._responses.popleft()

        if isinstance(
            item,
            Exception,
        ):
            raise item

        return item

    async def close(self) -> None:
        return None


def fake_usage() -> ModelUsage:
    return ModelUsage(
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
    )