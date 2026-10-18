from pydantic import SecretStr

from app.core.config import Settings
from app.llm.contracts import (
    ModelCapability,
    ModelSpec,
    ModelTask,
    ProviderName,
)
from app.llm.gateway import ModelGateway
from app.llm.health import ProviderHealthManager
from app.llm.providers.base import ProviderAdapter
from app.llm.providers.gemini import GeminiAdapter
from app.llm.providers.groq import GroqAdapter
from app.llm.providers.mistral import MistralAdapter
from app.llm.providers.ollama import OllamaAdapter
from app.llm.registry import ModelRegistry


def _secret_text(
    secret: SecretStr | None,
) -> str | None:
    if secret is None:
        return None

    value = (
        secret.get_secret_value()
        .strip()
    )

    return value or None


def build_model_gateway(
    settings: Settings,
) -> ModelGateway:
    common_tasks = {
        ModelTask.EVENT_UNDERSTANDING,
        ModelTask.BASIC_REASONING,
    }

    registry = ModelRegistry(
        models=[
            ModelSpec(
                key="groq-primary",
                provider=ProviderName.GROQ,
                model_id=settings.groq_model,
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.REASONING,
                    ModelCapability.STRUCTURED_OUTPUT,
                },
                tasks=common_tasks,
                priority=10,
                input_cost_per_million_usd=0.075,
                output_cost_per_million_usd=0.30,
            ),
            ModelSpec(
                key="gemini-primary",
                provider=ProviderName.GEMINI,
                model_id=settings.gemini_model,
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.REASONING,
                    ModelCapability.STRUCTURED_OUTPUT,
                    ModelCapability.VISION,
                },
                tasks=common_tasks,
                priority=20,
                input_cost_per_million_usd=0.75,
                output_cost_per_million_usd=3.75,
            ),
            ModelSpec(
                key="mistral-primary",
                provider=ProviderName.MISTRAL,
                model_id=settings.mistral_model,
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.REASONING,
                    ModelCapability.STRUCTURED_OUTPUT,
                    ModelCapability.VISION,
                },
                tasks=common_tasks,
                priority=30,
                input_cost_per_million_usd=0.15,
                output_cost_per_million_usd=0.60,
            ),
            ModelSpec(
                key="ollama-local",
                provider=ProviderName.OLLAMA,
                model_id=settings.ollama_model,
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.REASONING,
                    ModelCapability.STRUCTURED_OUTPUT,
                },
                tasks=common_tasks,
                priority=40,
                input_cost_per_million_usd=0.0,
                output_cost_per_million_usd=0.0,
                enabled=settings.enable_ollama,
            ),
        ]
    )

    adapters: dict[
        ProviderName,
        ProviderAdapter,
    ] = {}

    groq_key = _secret_text(
        settings.groq_api_key
    )

    if groq_key:
        adapters[
            ProviderName.GROQ
        ] = GroqAdapter(
            api_key=groq_key
        )

    gemini_key = _secret_text(
        settings.gemini_api_key
    )

    if gemini_key:
        adapters[
            ProviderName.GEMINI
        ] = GeminiAdapter(
            api_key=gemini_key
        )

    mistral_key = _secret_text(
        settings.mistral_api_key
    )

    if mistral_key:
        adapters[
            ProviderName.MISTRAL
        ] = MistralAdapter(
            api_key=mistral_key
        )

    if settings.enable_ollama:
        adapters[
            ProviderName.OLLAMA
        ] = OllamaAdapter(
            host=settings.ollama_host
        )

    health = ProviderHealthManager(
        failure_threshold=(
            settings.llm_circuit_failure_threshold
        ),
        cooldown_seconds=(
            settings.llm_circuit_cooldown_seconds
        ),
    )

    return ModelGateway(
        registry=registry,
        adapters=adapters,
        health=health,
        max_attempts=(
            settings.llm_max_attempts
        ),
        backoff_seconds=(
            settings.llm_backoff_seconds
        ),
    )