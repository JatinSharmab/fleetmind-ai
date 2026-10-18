import asyncio


class ModelGatewayError(Exception):
    """Base exception for FleetMind model infrastructure."""


class NoProviderAvailableError(ModelGatewayError):
    """All eligible model/provider options failed or were unavailable."""


class CircuitOpenError(ModelGatewayError):
    """Provider has been temporarily disabled by the circuit breaker."""


class ProviderCallError(ModelGatewayError):
    """Normalized provider failure."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        rate_limited: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)

        self.retryable = retryable
        self.rate_limited = rate_limited
        self.status_code = status_code


class StructuredOutputError(ModelGatewayError):
    """Provider returned output that failed FleetMind schema validation."""


def normalize_provider_exception(
    exc: Exception,
) -> ProviderCallError:
    """Translate provider-specific exceptions into FleetMind semantics."""

    if isinstance(exc, ProviderCallError):
        return exc

    if isinstance(
        exc,
        (asyncio.TimeoutError, TimeoutError, ConnectionError),
    ):
        return ProviderCallError(
            str(exc) or "Provider request timed out.",
            retryable=True,
        )

    status_code = getattr(
        exc,
        "status_code",
        None,
    )

    if status_code is None:
        response = getattr(
            exc,
            "response",
            None,
        )

        status_code = getattr(
            response,
            "status_code",
            None,
        )

    if status_code is None:
        code = getattr(
            exc,
            "code",
            None,
        )

        if isinstance(code, int):
            status_code = code

    text = str(exc)
    lower_text = text.lower()

    if status_code == 429 or "rate limit" in lower_text:
        return ProviderCallError(
            text,
            retryable=True,
            rate_limited=True,
            status_code=429,
        )

    if status_code in {400, 401, 403, 404, 422}:
        return ProviderCallError(
            text,
            retryable=False,
            status_code=status_code,
        )

    if isinstance(status_code, int) and status_code >= 500:
        return ProviderCallError(
            text,
            retryable=True,
            status_code=status_code,
        )

    return ProviderCallError(
        text,
        retryable=True,
        status_code=status_code,
    )