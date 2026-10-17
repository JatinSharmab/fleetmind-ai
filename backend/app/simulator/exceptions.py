class SimulationError(Exception):
    """Base exception for expected Digital Twin failures."""


class RouteUnavailableError(SimulationError):
    """No legal road path exists between two locations."""


class PackageMismatchError(SimulationError):
    """A package does not match the requested delivery."""


class InsufficientBatteryError(SimulationError):
    """The vehicle cannot safely complete the requested route."""