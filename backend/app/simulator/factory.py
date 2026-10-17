from app.events.publisher import EventPublisher
from app.simulator.city import build_demo_city
from app.simulator.engine import (
    DeterministicMissionRunner,
    DigitalTwin,
)
from app.simulator.models import (
    DeliveryStop,
    Mission,
    Package,
    VehicleState,
)


def build_demo_mission(
    publisher: EventPublisher,
) -> tuple[DeterministicMissionRunner, Mission]:
    city = build_demo_city()

    vehicle = VehicleState(
        vehicle_id="VAN-001",
        location="DEPOT",
        battery_percent=100.0,
        capacity_packages=10,
        loaded_package_ids=[
            "PKG-001",
            "PKG-002",
            "PKG-003",
        ],
    )

    deliveries = {
        "DEL-001": DeliveryStop(
            delivery_id="DEL-001",
            location="B",
            package_id="PKG-001",
            priority=3,
        ),
        "DEL-002": DeliveryStop(
            delivery_id="DEL-002",
            location="C",
            package_id="PKG-002",
            priority=4,
        ),
        "DEL-003": DeliveryStop(
            delivery_id="DEL-003",
            location="E",
            package_id="PKG-003",
            priority=2,
        ),
    }

    packages = {
        "PKG-001": Package(
            package_id="PKG-001",
            expected_delivery_id="DEL-001",
        ),
        "PKG-002": Package(
            package_id="PKG-002",
            expected_delivery_id="DEL-002",
        ),
        "PKG-003": Package(
            package_id="PKG-003",
            expected_delivery_id="DEL-003",
        ),
    }

    twin = DigitalTwin(
        city=city,
        vehicle=vehicle,
        packages=packages,
        deliveries=deliveries,
    )

    runner = DeterministicMissionRunner(
        twin=twin,
        publisher=publisher,
        depot_location="DEPOT",
    )

    mission = Mission(
        mission_id="MISSION-001",
        vehicle_id="VAN-001",
        delivery_ids=[
            "DEL-001",
            "DEL-002",
            "DEL-003",
        ],
    )

    return runner, mission