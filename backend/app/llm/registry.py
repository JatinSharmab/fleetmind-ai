from app.llm.contracts import (
    ModelCapability,
    ModelSpec,
    ModelTask,
    ProviderName,
)


class ModelRegistry:
    """Static model metadata and candidate selection."""

    def __init__(
        self,
        models: list[ModelSpec],
    ) -> None:
        self._models = {
            model.key: model
            for model in models
        }

    def all_models(
        self,
    ) -> list[ModelSpec]:
        return list(
            self._models.values()
        )

    def candidates(
        self,
        *,
        task: ModelTask,
        preferred_provider: ProviderName | None = None,
    ) -> list[ModelSpec]:
        models = [
            model
            for model in self._models.values()
            if (
                model.enabled
                and task in model.tasks
                and ModelCapability.STRUCTURED_OUTPUT
                in model.capabilities
            )
        ]

        def ranking(
            model: ModelSpec,
        ) -> tuple[int, int]:
            preferred_rank = 1

            if (
                preferred_provider is not None
                and model.provider
                == preferred_provider
            ):
                preferred_rank = 0

            return (
                preferred_rank,
                model.priority,
            )

        return sorted(
            models,
            key=ranking,
        )