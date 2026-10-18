from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)

from app.intelligence.models import (
    EventUnderstandingRequest,
    EventUnderstandingResponse,
)
from app.intelligence.service import (
    EventIntelligenceService,
)
from app.llm.errors import (
    NoProviderAvailableError,
)


router = APIRouter(
    prefix="/api/v1/intelligence",
    tags=["intelligence"],
)


@router.post(
    "/events/analyze",
    response_model=EventUnderstandingResponse,
)
async def analyze_event(
    body: EventUnderstandingRequest,
    request: Request,
) -> EventUnderstandingResponse:
    service = EventIntelligenceService(
        gateway=(
            request.app.state.model_gateway
        )
    )

    try:
        return await service.analyze(
            body
        )

    except NoProviderAvailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc