from fastapi import APIRouter, Request

from app.simulator.factory import build_demo_mission
from app.simulator.models import SimulationResult


router = APIRouter(
    prefix="/api/v1/simulations",
    tags=["simulation"],
)


@router.post(
    "/demo/run",
    response_model=SimulationResult,
)
async def run_demo_simulation(
    request: Request,
) -> SimulationResult:
    publisher = request.app.state.event_publisher

    runner, mission = build_demo_mission(
        publisher
    )

    return await runner.run(
        mission
    )