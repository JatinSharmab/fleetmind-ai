import pytest

from app.intelligence.models import (
    EventUnderstanding,
)
from app.llm.contracts import (
    ModelCapability,
    ModelSpec,
    ModelTask,
    ProviderName,
    ProviderResult,
    StructuredGenerationRequest,
)
from app.llm.errors import (
    ProviderCallError,
)
from app.llm.gateway import ModelGateway
from app.llm.health import (
    ProviderHealthManager,
)
from app.llm.registry import ModelRegistry
from tests.fakes import (
    FakeProviderAdapter,
    fake_usage,
)


def make_output() -> str:
    return EventUnderstanding(
        category="road.blocked",
        urgency="high",
        affected_entity="C-E",
        summary="Road C-E is blocked.",
        likely_impact="Current route may be unavailable.",
        recommended_capability="route",
        should_interrupt_current_mission=True,
        confidence=0.97,
        facts=[
            "Road C-E is blocked."
        ],
        assumptions=[],
    ).model_dump_json()


def make_registry() -> ModelRegistry:
    return ModelRegistry(
        [
            ModelSpec(
                key="groq-test",
                provider=ProviderName.GROQ,
                model_id="fake-groq",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.STRUCTURED_OUTPUT,
                },
                tasks={
                    ModelTask.EVENT_UNDERSTANDING,
                },
                priority=10,
                input_cost_per_million_usd=1,
                output_cost_per_million_usd=1,
            ),
            ModelSpec(
                key="gemini-test",
                provider=ProviderName.GEMINI,
                model_id="fake-gemini",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.STRUCTURED_OUTPUT,
                },
                tasks={
                    ModelTask.EVENT_UNDERSTANDING,
                },
                priority=20,
                input_cost_per_million_usd=1,
                output_cost_per_million_usd=1,
            ),
        ]
    )


def make_request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        task=ModelTask.EVENT_UNDERSTANDING,
        system_prompt="Classify.",
        user_prompt="Road blocked.",
        timeout_seconds=1,
    )


@pytest.mark.asyncio
async def test_gateway_validates_structured_output() -> None:
    groq = FakeProviderAdapter(
        name=ProviderName.GROQ,
        responses=[
            ProviderResult(
                text=make_output(),
                usage=fake_usage(),
            )
        ],
    )

    gateway = ModelGateway(
        registry=make_registry(),
        adapters={
            ProviderName.GROQ: groq,
        },
        health=ProviderHealthManager(
            failure_threshold=3,
            cooldown_seconds=30,
        ),
        max_attempts=2,
        backoff_seconds=0,
    )

    result = await gateway.generate_structured(
        request=make_request(),
        response_model=EventUnderstanding,
    )

    assert (
        result.output.category
        == "road.blocked"
    )

    assert (
        result.metadata.provider
        == ProviderName.GROQ
    )

    assert result.metadata.attempts == 1


@pytest.mark.asyncio
async def test_rate_limit_falls_back_to_gemini() -> None:
    groq = FakeProviderAdapter(
        name=ProviderName.GROQ,
        responses=[
            ProviderCallError(
                "rate limited",
                retryable=True,
                rate_limited=True,
                status_code=429,
            )
        ],
    )

    gemini = FakeProviderAdapter(
        name=ProviderName.GEMINI,
        responses=[
            ProviderResult(
                text=make_output(),
                usage=fake_usage(),
            )
        ],
    )

    gateway = ModelGateway(
        registry=make_registry(),
        adapters={
            ProviderName.GROQ: groq,
            ProviderName.GEMINI: gemini,
        },
        health=ProviderHealthManager(
            failure_threshold=3,
            cooldown_seconds=30,
        ),
        max_attempts=2,
        backoff_seconds=0,
    )

    result = await gateway.generate_structured(
        request=make_request(),
        response_model=EventUnderstanding,
    )

    assert (
        result.metadata.provider
        == ProviderName.GEMINI
    )

    assert groq.calls == 1
    assert gemini.calls == 1


@pytest.mark.asyncio
async def test_malformed_output_retries_then_falls_back() -> None:
    groq = FakeProviderAdapter(
        name=ProviderName.GROQ,
        responses=[
            ProviderResult(
                text='{"wrong":"shape"}',
                usage=fake_usage(),
            ),
            ProviderResult(
                text='{"still":"wrong"}',
                usage=fake_usage(),
            ),
        ],
    )

    gemini = FakeProviderAdapter(
        name=ProviderName.GEMINI,
        responses=[
            ProviderResult(
                text=make_output(),
                usage=fake_usage(),
            )
        ],
    )

    gateway = ModelGateway(
        registry=make_registry(),
        adapters={
            ProviderName.GROQ: groq,
            ProviderName.GEMINI: gemini,
        },
        health=ProviderHealthManager(
            failure_threshold=3,
            cooldown_seconds=30,
        ),
        max_attempts=2,
        backoff_seconds=0,
    )

    result = await gateway.generate_structured(
        request=make_request(),
        response_model=EventUnderstanding,
    )

    assert groq.calls == 2

    assert (
        result.metadata.provider
        == ProviderName.GEMINI
    )