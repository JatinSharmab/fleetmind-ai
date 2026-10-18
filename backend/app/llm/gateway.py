import asyncio
import logging
from time import perf_counter
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.contracts import (
    GatewayResult,
    ModelCallMetadata,
    ModelUsage,
    ProviderName,
    StructuredGenerationRequest,
)
from app.llm.errors import (
    NoProviderAvailableError,
    ProviderCallError,
    StructuredOutputError,
    normalize_provider_exception,
)
from app.llm.health import ProviderHealthManager
from app.llm.providers.base import ProviderAdapter
from app.llm.registry import ModelRegistry


logger = logging.getLogger(__name__)


TModel = TypeVar(
    "TModel",
    bound=BaseModel,
)


class ModelGateway:
    """Provider-independent access point for FleetMind model inference."""

    def __init__(
        self,
        *,
        registry: ModelRegistry,
        adapters: dict[
            ProviderName,
            ProviderAdapter,
        ],
        health: ProviderHealthManager,
        max_attempts: int,
        backoff_seconds: float,
    ) -> None:
        self.registry = registry
        self._adapters = adapters
        self._health = health
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds

    @property
    def configured_providers(
        self,
    ) -> set[ProviderName]:
        return set(
            self._adapters.keys()
        )

    @staticmethod
    def _estimate_cost(
        *,
        input_tokens: int | None,
        output_tokens: int | None,
        input_cost_per_million: float | None,
        output_cost_per_million: float | None,
    ) -> float | None:
        if (
            input_tokens is None
            or output_tokens is None
            or input_cost_per_million is None
            or output_cost_per_million is None
        ):
            return None

        input_cost = (
            input_tokens
            / 1_000_000
            * input_cost_per_million
        )

        output_cost = (
            output_tokens
            / 1_000_000
            * output_cost_per_million
        )

        return round(
            input_cost + output_cost,
            8,
        )

    async def generate_structured(
        self,
        *,
        request: StructuredGenerationRequest,
        response_model: type[TModel],
    ) -> GatewayResult[TModel]:
        started = perf_counter()

        candidates = self.registry.candidates(
            task=request.task,
            preferred_provider=(
                request.preferred_provider
            ),
        )

        failures: list[str] = []
        total_attempts = 0

        for model in candidates:
            adapter = self._adapters.get(
                model.provider
            )

            if adapter is None:
                continue

            available = (
                await self._health.is_available(
                    model.provider
                )
            )

            if not available:
                failures.append(
                    f"{model.provider.value}:circuit_open"
                )
                continue

            for attempt in range(
                1,
                self._max_attempts + 1,
            ):
                total_attempts += 1
                call_started = perf_counter()

                try:
                    raw_result = await asyncio.wait_for(
                        adapter.generate_structured(
                            model=model,
                            request=request,
                            response_model=response_model,
                        ),
                        timeout=request.timeout_seconds,
                    )

                    try:
                        output = (
                            response_model.model_validate_json(
                                raw_result.text
                            )
                        )

                    except ValidationError as exc:
                        raise StructuredOutputError(
                            "Model returned output that failed "
                            "FleetMind schema validation."
                        ) from exc

                    await self._health.record_success(
                        model.provider
                    )

                    provider_latency_ms = (
                        perf_counter()
                        - call_started
                    ) * 1000

                    total_latency_ms = (
                        perf_counter()
                        - started
                    ) * 1000

                    estimated_cost = (
                        self._estimate_cost(
                            input_tokens=(
                                raw_result.usage.input_tokens
                            ),
                            output_tokens=(
                                raw_result.usage.output_tokens
                            ),
                            input_cost_per_million=(
                                model.input_cost_per_million_usd
                            ),
                            output_cost_per_million=(
                                model.output_cost_per_million_usd
                            ),
                        )
                    )

                    metadata = ModelCallMetadata(
                        provider=model.provider,
                        model=model.model_id,
                        attempts=total_attempts,
                        fallbacks=failures.copy(),
                        provider_latency_ms=round(
                            provider_latency_ms,
                            3,
                        ),
                        total_latency_ms=round(
                            total_latency_ms,
                            3,
                        ),
                        usage=raw_result.usage,
                        estimated_list_cost_usd=(
                            estimated_cost
                        ),
                    )

                    logger.info(
                        "model_call_succeeded",
                        extra={
                            "provider": (
                                model.provider.value
                            ),
                            "model": model.model_id,
                            "task": request.task.value,
                            "input_tokens": (
                                raw_result.usage.input_tokens
                            ),
                            "output_tokens": (
                                raw_result.usage.output_tokens
                            ),
                            "latency_ms": round(
                                provider_latency_ms,
                                3,
                            ),
                        },
                    )

                    return GatewayResult[
                        TModel
                    ](
                        output=output,
                        metadata=metadata,
                    )

                except StructuredOutputError as exc:
                    normalized = ProviderCallError(
                        str(exc),
                        retryable=True,
                    )

                except Exception as exc:
                    normalized = (
                        normalize_provider_exception(
                            exc
                        )
                    )

                await self._health.record_failure(
                    model.provider,
                    error=str(normalized),
                    rate_limited=(
                        normalized.rate_limited
                    ),
                )

                logger.warning(
                    "model_call_failed",
                    extra={
                        "provider": (
                            model.provider.value
                        ),
                        "model": model.model_id,
                        "task": request.task.value,
                        "attempt": attempt,
                        "rate_limited": (
                            normalized.rate_limited
                        ),
                    },
                )

                failure_label = (
                    f"{model.provider.value}:"
                    f"{normalized.status_code or 'error'}"
                )

                failures.append(
                    failure_label
                )

                if normalized.rate_limited:
                    break

                if not normalized.retryable:
                    break

                if attempt >= self._max_attempts:
                    break

                delay = (
                    self._backoff_seconds
                    * (
                        2
                        ** (
                            attempt - 1
                        )
                    )
                )

                await asyncio.sleep(
                    delay
                )

        raise NoProviderAvailableError(
            "No configured healthy model provider "
            f"completed task {request.task.value}. "
            f"Failures: {failures}"
        )

    async def health_snapshot(
        self,
    ) -> dict[str, dict]:
        return await self._health.snapshot()

    async def close(
        self,
    ) -> None:
        for adapter in self._adapters.values():
            try:
                await adapter.close()
            except Exception:
                logger.exception(
                    "model_adapter_close_failed",
                )