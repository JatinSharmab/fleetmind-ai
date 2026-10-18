import asyncio
from dataclasses import dataclass
from time import monotonic

from app.llm.contracts import ProviderName


@dataclass
class ProviderHealthState:
    consecutive_failures: int = 0
    open_until: float = 0.0
    last_error: str | None = None


class ProviderHealthManager:
    """Small in-process provider circuit breaker."""

    def __init__(
        self,
        *,
        failure_threshold: int,
        cooldown_seconds: float,
    ) -> None:
        self._failure_threshold = (
            failure_threshold
        )

        self._cooldown_seconds = (
            cooldown_seconds
        )

        self._states: dict[
            ProviderName,
            ProviderHealthState,
        ] = {}

        self._lock = asyncio.Lock()

    async def is_available(
        self,
        provider: ProviderName,
    ) -> bool:
        async with self._lock:
            state = self._states.setdefault(
                provider,
                ProviderHealthState(),
            )

            return monotonic() >= (
                state.open_until
            )

    async def record_success(
        self,
        provider: ProviderName,
    ) -> None:
        async with self._lock:
            state = self._states.setdefault(
                provider,
                ProviderHealthState(),
            )

            state.consecutive_failures = 0
            state.open_until = 0.0
            state.last_error = None

    async def record_failure(
        self,
        provider: ProviderName,
        *,
        error: str,
        rate_limited: bool,
    ) -> None:
        async with self._lock:
            state = self._states.setdefault(
                provider,
                ProviderHealthState(),
            )

            state.consecutive_failures += 1
            state.last_error = error

            should_open = (
                rate_limited
                or state.consecutive_failures
                >= self._failure_threshold
            )

            if should_open:
                state.open_until = (
                    monotonic()
                    + self._cooldown_seconds
                )

    async def snapshot(
        self,
    ) -> dict[str, dict]:
        async with self._lock:
            now = monotonic()

            result: dict[str, dict] = {}

            for provider, state in self._states.items():
                remaining = max(
                    0.0,
                    state.open_until - now,
                )

                result[provider.value] = {
                    "available": (
                        remaining == 0
                    ),
                    "consecutive_failures": (
                        state.consecutive_failures
                    ),
                    "cooldown_remaining_seconds": round(
                        remaining,
                        3,
                    ),
                    "last_error": state.last_error,
                }

            return result