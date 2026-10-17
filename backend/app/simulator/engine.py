import logging
from uuid import UUID, uuid4

from app.events.models import EventType, FleetEvent
from app.events.publisher import EventPublisher
from app.simulator.city import CityGraph
from app.simulator.exceptions import (
    InsufficientBatteryError,
    PackageMismatchError,
    SimulationError,
)
from app.simulator.models import (
    DeliveryStatus,
    DeliveryStop,
    Mission,
    MissionStatus,
    MovementObservation,
    Package,
    PackageStatus,
    RoutePlan,
    SimulationResult,
    VehicleState,
    VehicleStatus,
)


logger = logging.getLogger(__name__)

BATTERY_DRAIN_PERCENT_PER_KM = 1.5
LOW_BATTERY_THRESHOLD_PERCENT = 20.0


class DigitalTwin:
    """Mutable simulation of the delivery van and its environment."""

    def __init__(
        self,
        *,
        city: CityGraph,
        vehicle: VehicleState,
        packages: dict[str, Package],
        deliveries: dict[str, DeliveryStop],
    ) -> None:
        self.city = city
        self.vehicle = vehicle
        self.packages = packages
        self.deliveries = deliveries

    def plan_route(self, destination: str) -> RoutePlan:
        return self.city.shortest_route(
            source=self.vehicle.location,
            destination=destination,
        )

    def move_along(
        self,
        route: RoutePlan,
    ) -> list[MovementObservation]:
        required_battery = (
            route.distance_km * BATTERY_DRAIN_PERCENT_PER_KM
        )

        if required_battery > self.vehicle.battery_percent:
            raise InsufficientBatteryError(
                "Vehicle does not have enough battery for route "
                f"{self.vehicle.location} -> {route.nodes[-1]}."
            )

        observations: list[MovementObservation] = []

        self.vehicle.status = VehicleStatus.MOVING

        for start, end in zip(
            route.nodes,
            route.nodes[1:],
            strict=False,
        ):
            distance_km, travel_minutes = self.city.get_edge_metrics(
                start,
                end,
            )

            battery_drain = (
                distance_km * BATTERY_DRAIN_PERCENT_PER_KM
            )

            self.vehicle.battery_percent = round(
                self.vehicle.battery_percent - battery_drain,
                3,
            )

            self.vehicle.location = end

            observations.append(
                MovementObservation(
                    from_location=start,
                    to_location=end,
                    segment_distance_km=distance_km,
                    segment_travel_minutes=travel_minutes,
                    battery_percent=self.vehicle.battery_percent,
                )
            )

        self.vehicle.status = VehicleStatus.IDLE

        return observations

    def verify_package_for_delivery(
        self,
        delivery_id: str,
    ) -> Package:
        delivery = self.deliveries[delivery_id]
        package = self.packages[delivery.package_id]

        if package.package_id not in self.vehicle.loaded_package_ids:
            raise PackageMismatchError(
                f"Package {package.package_id} is not loaded in vehicle "
                f"{self.vehicle.vehicle_id}."
            )

        if package.expected_delivery_id != delivery_id:
            raise PackageMismatchError(
                f"Package {package.package_id} expects delivery "
                f"{package.expected_delivery_id}, not {delivery_id}."
            )

        if package.status != PackageStatus.LOADED:
            raise PackageMismatchError(
                f"Package {package.package_id} is not in LOADED state."
            )

        return package

    def complete_delivery(
        self,
        delivery_id: str,
    ) -> None:
        delivery = self.deliveries[delivery_id]

        package = self.verify_package_for_delivery(delivery_id)

        if self.vehicle.location != delivery.location:
            raise SimulationError(
                f"Vehicle is at {self.vehicle.location}, "
                f"but delivery {delivery_id} requires {delivery.location}."
            )

        package.status = PackageStatus.DELIVERED
        delivery.status = DeliveryStatus.COMPLETED

        self.vehicle.loaded_package_ids.remove(package.package_id)


class DeterministicMissionRunner:
    """Non-AI baseline mission executor."""

    def __init__(
        self,
        *,
        twin: DigitalTwin,
        publisher: EventPublisher,
        depot_location: str = "DEPOT",
    ) -> None:
        self.twin = twin
        self.publisher = publisher
        self.depot_location = depot_location

        self._events: list[FleetEvent] = []
        self._route_history: list[str] = [
            self.twin.vehicle.location
        ]

        self._distance_km = 0.0
        self._travel_minutes = 0.0

        self._low_battery_emitted = False

    async def _emit(
        self,
        *,
        event_type: EventType,
        mission: Mission,
        correlation_id: UUID,
        payload: dict,
    ) -> None:
        event = FleetEvent(
            event_type=event_type,
            source="digital-twin",
            mission_id=mission.mission_id,
            vehicle_id=mission.vehicle_id,
            correlation_id=correlation_id,
            payload=payload,
        )

        self._events.append(event)

        await self.publisher.publish(event)

        logger.info(
            "fleet_event_emitted",
            extra={
                "mission_id": mission.mission_id,
                "vehicle_id": mission.vehicle_id,
                "event_id": str(event.event_id),
                "event_type": event.event_type.value,
            },
        )

    async def _execute_route(
        self,
        *,
        mission: Mission,
        route: RoutePlan,
        correlation_id: UUID,
    ) -> None:
        observations = self.twin.move_along(route)

        for observation in observations:
            self._route_history.append(
                observation.to_location
            )

            self._distance_km += (
                observation.segment_distance_km
            )

            self._travel_minutes += (
                observation.segment_travel_minutes
            )

            await self._emit(
                event_type=EventType.VEHICLE_LOCATION_CHANGED,
                mission=mission,
                correlation_id=correlation_id,
                payload={
                    "from_location": observation.from_location,
                    "to_location": observation.to_location,
                    "segment_distance_km": (
                        observation.segment_distance_km
                    ),
                    "segment_travel_minutes": (
                        observation.segment_travel_minutes
                    ),
                    "battery_percent": (
                        observation.battery_percent
                    ),
                },
            )

            if (
                observation.battery_percent
                <= LOW_BATTERY_THRESHOLD_PERCENT
                and not self._low_battery_emitted
            ):
                self._low_battery_emitted = True

                await self._emit(
                    event_type=EventType.BATTERY_LOW,
                    mission=mission,
                    correlation_id=correlation_id,
                    payload={
                        "battery_percent": (
                            observation.battery_percent
                        )
                    },
                )

    async def run(
        self,
        mission: Mission,
    ) -> SimulationResult:
        correlation_id = uuid4()

        mission.status = MissionStatus.RUNNING

        await self._emit(
            event_type=EventType.MISSION_STARTED,
            mission=mission,
            correlation_id=correlation_id,
            payload={
                "delivery_ids": mission.delivery_ids,
                "starting_location": self.twin.vehicle.location,
            },
        )

        try:
            for delivery_id in mission.delivery_ids:
                delivery = self.twin.deliveries[delivery_id]

                route = self.twin.plan_route(
                    delivery.location
                )

                await self._execute_route(
                    mission=mission,
                    route=route,
                    correlation_id=correlation_id,
                )

                self.twin.complete_delivery(
                    delivery_id
                )

                await self._emit(
                    event_type=EventType.DELIVERY_COMPLETED,
                    mission=mission,
                    correlation_id=correlation_id,
                    payload={
                        "delivery_id": delivery.delivery_id,
                        "package_id": delivery.package_id,
                        "location": delivery.location,
                    },
                )

            if self.twin.vehicle.location != self.depot_location:
                return_route = self.twin.plan_route(
                    self.depot_location
                )

                await self._execute_route(
                    mission=mission,
                    route=return_route,
                    correlation_id=correlation_id,
                )

            mission.status = MissionStatus.COMPLETED

            await self._emit(
                event_type=EventType.MISSION_COMPLETED,
                mission=mission,
                correlation_id=correlation_id,
                payload={
                    "distance_km": round(
                        self._distance_km,
                        3,
                    ),
                    "travel_minutes": round(
                        self._travel_minutes,
                        3,
                    ),
                    "final_battery_percent": (
                        self.twin.vehicle.battery_percent
                    ),
                },
            )

        except SimulationError as exc:
            mission.status = MissionStatus.FAILED

            await self._emit(
                event_type=EventType.MISSION_FAILED,
                mission=mission,
                correlation_id=correlation_id,
                payload={
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                },
            )

            raise

        return SimulationResult(
            mission_id=mission.mission_id,
            mission_status=mission.status,
            vehicle=self.twin.vehicle,
            deliveries=list(
                self.twin.deliveries.values()
            ),
            packages=list(
                self.twin.packages.values()
            ),
            route_history=self._route_history,
            total_distance_km=round(
                self._distance_km,
                3,
            ),
            total_travel_minutes=round(
                self._travel_minutes,
                3,
            ),
            events=self._events,
        )