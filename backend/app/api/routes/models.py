from fastapi import (
    APIRouter,
    Request,
)


router = APIRouter(
    prefix="/api/v1/models",
    tags=["models"],
)


@router.get("")
async def list_models(
    request: Request,
) -> dict:
    gateway = (
        request.app.state.model_gateway
    )

    configured = {
        provider.value
        for provider
        in gateway.configured_providers
    }

    models = []

    for model in gateway.registry.all_models():
        models.append(
            {
                **model.model_dump(
                    mode="json"
                ),
                "provider_configured": (
                    model.provider.value
                    in configured
                ),
            }
        )

    return {
        "models": models
    }


@router.get("/health")
async def model_health(
    request: Request,
) -> dict:
    gateway = (
        request.app.state.model_gateway
    )

    return {
        "configured_providers": [
            provider.value
            for provider
            in gateway.configured_providers
        ],
        "health": (
            await gateway.health_snapshot()
        ),
    }