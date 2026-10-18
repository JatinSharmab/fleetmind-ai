from typing import TypeVar

from ollama import AsyncClient
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


class OllamaAdapter:
    name = ProviderName.OLLAMA

    def __init__(
        self,
        *,
        host: str,
    ) -> None:
        self._client = AsyncClient(
            host=host,
        )

    async def generate_structured(
        self,
        *,
        model: ModelSpec,
        request: StructuredGenerationRequest,
        response_model: type[TModel],
    ) -> ProviderResult:
        response = await self._client.chat(
            model=model.model_id,
            messages=[
                {
                    "role": "system",
                    "content": request.system_prompt,
                },
                {
                    "role": "user",
                    "content": request.user_prompt,
                },
            ],
            format=response_model.model_json_schema(),
            options={
                "temperature": request.temperature,
                "num_predict": request.max_output_tokens,
            },
        )

        input_tokens = getattr(
            response,
            "prompt_eval_count",
            None,
        )

        output_tokens = getattr(
            response,
            "eval_count",
            None,
        )

        total_tokens: int | None = None

        if (
            input_tokens is not None
            and output_tokens is not None
        ):
            total_tokens = (
                input_tokens
                + output_tokens
            )

        return ProviderResult(
            text=response.message.content,
            usage=ModelUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
            finish_reason="stop",
        )

    async def close(self) -> None:
        await self._client.close()