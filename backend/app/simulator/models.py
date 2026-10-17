from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.events.models import FleetEvent


class VehicleStatus(StrEnum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    STOPPED = "STOPPED"


class PackageStatus(StrEnum):
    LOADED = "LOADED"
    DELIVERED = "DELIVERED"


class DeliveryStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MissionStatus(StrEnum):
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VehicleState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vehicle_id: str
    location: str

    battery_percent: float = Field(ge=0, le=100)

    status: VehicleStatus = VehicleStatus.IDLE

    capacity_packages: int = Field(gt=0)

    loaded_package_ids: list[str] = Field(default_factory=list)


class Package(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_id: str
    expected_delivery_id: str
    status: PackageStatus = PackageStatus.LOADED


class DeliveryStop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_id: str
    location: str
    package_id: str

    priority: int = Field(default=3, ge=1, le=5)

    status: DeliveryStatus = DeliveryStatus.PENDING


class Mission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission_id: str
    vehicle_id: str

    delivery_ids: list[str]

    status: MissionStatus = MissionStatus.READY


class RoutePlan(BaseModel):
    nodes: list[str]
    distance_km: float
    travel_minutes: float


class MovementObservation(BaseModel):
    from_location: str
    to_location: str

    segment_distance_km: float
    segment_travel_minutes: float

    battery_percent: float


class SimulationResult(BaseModel):
    mission_id: str
    mission_status: MissionStatus

    vehicle: VehicleState

    deliveries: list[DeliveryStop]
    packages: list[Package]

    route_history: list[str]

    total_distance_km: float
    total_travel_minutes: float

    events: list[FleetEvent]