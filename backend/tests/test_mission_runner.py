import pytest

from app.events.models import EventType
from app.events.publisher import InMemoryEventPublisher
from app.simulator.exceptions import (
    InsufficientBatteryError,
    PackageMismatchError,
)
from app.simulator.factory import build_demo_mission
from app.simulator.models import MissionStatus


@pytest.mark.asyncio
async def test_demo_mission_completes() -> None:
    publisher = InMemoryEventPublisher()

    runner, mission = build_demo_mission(
        publisher
    )

    result = await runner.run(
        mission
    )

    assert (
        result.mission_status
        == MissionStatus.COMPLETED
    )

    assert result.vehicle.location == "DEPOT"

    assert all(
        delivery.status == "COMPLETED"
        for delivery in result.deliveries
    )

    assert result.total_distance_km == 13.0

    event_types = {
        event.event_type
        for event in result.events
    }

    assert (
        EventType.MISSION_STARTED
        in event_types
    )

    assert (
        EventType.MISSION_COMPLETED
        in event_types
    )


@pytest.mark.asyncio
async def test_package_mismatch_fails_mission() -> None:
    publisher = InMemoryEventPublisher()

    runner, mission = build_demo_mission(
        publisher
    )

    runner.twin.packages[
        "PKG-001"
    ].expected_delivery_id = "DEL-999"

    with pytest.raises(
        PackageMismatchError
    ):
        await runner.run(
            mission
        )

    assert (
        mission.status
        == MissionStatus.FAILED
    )

    assert (
        publisher.events[-1].event_type
        == EventType.MISSION_FAILED
    )


@pytest.mark.asyncio
async def test_insufficient_battery_fails() -> None:
    publisher = InMemoryEventPublisher()

    runner, mission = build_demo_mission(
        publisher
    )

    runner.twin.vehicle.battery_percent = 1.0

    with pytest.raises(
        InsufficientBatteryError
    ):
        await runner.run(
            mission
        )

    assert (
        mission.status
        == MissionStatus.FAILED
    )