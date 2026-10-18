from typing import TypeVar

from groq import AsyncGroq
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


class GroqAdapter:
    name = ProviderName.GROQ

    def __init__(
        self,
        *,
        api_key: str,
    ) -> None:
        self._client = AsyncGroq(
            api_key=api_key,
        )

    async def generate_structured(
        self,
        *,
        model: ModelSpec,
        request: StructuredGenerationRequest,
        response_model: type[TModel],
    ) -> ProviderResult:
        schema = response_model.model_json_schema()

        completion = await self._client.chat.completions.create(
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
            temperature=request.temperature,
            max_completion_tokens=request.max_output_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__.lower(),
                    "strict": True,
                    "schema": schema,
                },
            },
        )

        content = (
            completion.choices[0].message.content
            or ""
        )

        usage = completion.usage

        return ProviderResult(
            text=content,
            usage=ModelUsage(
                input_tokens=(
                    usage.prompt_tokens
                    if usage
                    else None
                ),
                output_tokens=(
                    usage.completion_tokens
                    if usage
                    else None
                ),
                total_tokens=(
                    usage.total_tokens
                    if usage
                    else None
                ),
            ),
            finish_reason=(
                completion.choices[0].finish_reason
            ),
        )

    async def close(self) -> None:
        await self._client.close()