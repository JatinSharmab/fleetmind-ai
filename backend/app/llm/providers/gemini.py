from typing import TypeVar

from google import genai
from google.genai import types
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


class GeminiAdapter:
    name = ProviderName.GEMINI

    def __init__(
        self,
        *,
        api_key: str,
    ) -> None:
        self._client = genai.Client(
            api_key=api_key,
        )

    async def generate_structured(
        self,
        *,
        model: ModelSpec,
        request: StructuredGenerationRequest,
        response_model: type[TModel],
    ) -> ProviderResult:
        response = await self._client.aio.models.generate_content(
            model=model.model_id,
            contents=request.user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=request.system_prompt,
                temperature=request.temperature,
                max_output_tokens=request.max_output_tokens,
                response_mime_type="application/json",
                response_schema=response_model,
                automatic_function_calling=(
                    types.AutomaticFunctionCallingConfig(
                        disable=True,
                    )
                ),
            ),
        )

        usage_metadata = response.usage_metadata

        input_tokens = getattr(
            usage_metadata,
            "prompt_token_count",
            None,
        )

        output_tokens = getattr(
            usage_metadata,
            "candidates_token_count",
            None,
        )

        total_tokens = getattr(
            usage_metadata,
            "total_token_count",
            None,
        )

        finish_reason: str | None = None

        if response.candidates:
            raw_reason = getattr(
                response.candidates[0],
                "finish_reason",
                None,
            )

            if raw_reason is not None:
                finish_reason = str(
                    raw_reason
                )

        return ProviderResult(
            text=response.text or "",
            usage=ModelUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
            finish_reason=finish_reason,
        )

    async def close(self) -> None:
        await self._client.aio.aclose()
        self._client.close()