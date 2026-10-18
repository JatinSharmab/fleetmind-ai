from typing import TypeVar

from mistralai.client import Mistral
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


class MistralAdapter:
    name = ProviderName.MISTRAL

    def __init__(
        self,
        *,
        api_key: str,
    ) -> None:
        self._client = Mistral(
            api_key=api_key,
        )

    async def generate_structured(
        self,
        *,
        model: ModelSpec,
        request: StructuredGenerationRequest,
        response_model: type[TModel],
    ) -> ProviderResult:
        response = await self._client.chat.complete_async(
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
            max_tokens=request.max_output_tokens,
            response_format=response_model,
        )

        content = response.choices[0].message.content

        if isinstance(
            content,
            str,
        ):
            text = content

        elif isinstance(
            content,
            list,
        ):
            text = "".join(
                str(
                    getattr(
                        item,
                        "text",
                        "",
                    )
                )
                for item in content
            )

        else:
            text = str(
                content or ""
            )

        usage = response.usage

        return ProviderResult(
            text=text,
            usage=ModelUsage(
                input_tokens=getattr(
                    usage,
                    "prompt_tokens",
                    None,
                ),
                output_tokens=getattr(
                    usage,
                    "completion_tokens",
                    None,
                ),
                total_tokens=getattr(
                    usage,
                    "total_tokens",
                    None,
                ),
            ),
            finish_reason=str(
                response.choices[0].finish_reason
            ),
        )

    async def close(self) -> None:
        await self._client.__aexit__(
            None,
            None,
            None,
        )