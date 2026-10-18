import pytest

from app.llm.contracts import (
    ProviderName,
)
from app.llm.health import (
    ProviderHealthManager,
)


@pytest.mark.asyncio
async def test_rate_limit_opens_circuit_immediately() -> None:
    health = ProviderHealthManager(
        failure_threshold=3,
        cooldown_seconds=30,
    )

    assert await health.is_available(
        ProviderName.GROQ
    )

    await health.record_failure(
        ProviderName.GROQ,
        error="429",
        rate_limited=True,
    )

    assert not await health.is_available(
        ProviderName.GROQ
    )