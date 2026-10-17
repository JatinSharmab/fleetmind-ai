from collections.abc import Callable

import networkx as nx

from app.simulator.exceptions import RouteUnavailableError
from app.simulator.models import RoutePlan


class CityGraph:
    """Graph representation of the simulated FleetMind city."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_location(self, location: str) -> None:
        self.graph.add_node(location)

    def add_bidirectional_road(
        self,
        start: str,
        end: str,
        *,
        distance_km: float,
        base_travel_minutes: float,
    ) -> None:
        attributes = {
            "distance_km": distance_km,
            "base_travel_minutes": base_travel_minutes,
            "traffic_multiplier": 1.0,
            "blocked": False,
        }

        self.graph.add_edge(start, end, **attributes)
        self.graph.add_edge(end, start, **attributes)

    @staticmethod
    def _travel_time_weight(
        _start: str,
        _end: str,
        attributes: dict,
    ) -> float | None:
        if attributes["blocked"]:
            return None

        return (
            float(attributes["base_travel_minutes"])
            * float(attributes["traffic_multiplier"])
        )

    def shortest_route(
        self,
        source: str,
        destination: str,
    ) -> RoutePlan:
        try:
            nodes = nx.shortest_path(
                self.graph,
                source=source,
                target=destination,
                weight=self._travel_time_weight,
                method="dijkstra",
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
            raise RouteUnavailableError(
                f"No available route from {source} to {destination}."
            ) from exc

        distance_km = 0.0
        travel_minutes = 0.0

        for start, end in zip(nodes, nodes[1:], strict=False):
            edge = self.graph[start][end]

            distance_km += float(edge["distance_km"])
            travel_minutes += (
                float(edge["base_travel_minutes"])
                * float(edge["traffic_multiplier"])
            )

        return RoutePlan(
            nodes=nodes,
            distance_km=round(distance_km, 3),
            travel_minutes=round(travel_minutes, 3),
        )

    def get_edge_metrics(
        self,
        start: str,
        end: str,
    ) -> tuple[float, float]:
        edge = self.graph[start][end]

        distance = float(edge["distance_km"])
        travel_minutes = (
            float(edge["base_travel_minutes"])
            * float(edge["traffic_multiplier"])
        )

        return distance, travel_minutes

    def set_road_blocked(
        self,
        start: str,
        end: str,
        blocked: bool = True,
        *,
        bidirectional: bool = True,
    ) -> None:
        self.graph[start][end]["blocked"] = blocked

        if bidirectional and self.graph.has_edge(end, start):
            self.graph[end][start]["blocked"] = blocked

    def set_traffic_multiplier(
        self,
        start: str,
        end: str,
        multiplier: float,
        *,
        bidirectional: bool = True,
    ) -> None:
        if multiplier <= 0:
            raise ValueError("Traffic multiplier must be greater than zero.")

        self.graph[start][end]["traffic_multiplier"] = multiplier

        if bidirectional and self.graph.has_edge(end, start):
            self.graph[end][start]["traffic_multiplier"] = multiplier


def build_demo_city() -> CityGraph:
    city = CityGraph()

    locations = [
        "DEPOT",
        "A",
        "B",
        "C",
        "D",
        "E",
        "CHARGER_1",
    ]

    for location in locations:
        city.add_location(location)

    city.add_bidirectional_road(
        "DEPOT",
        "A",
        distance_km=2.0,
        base_travel_minutes=4.0,
    )

    city.add_bidirectional_road(
        "A",
        "B",
        distance_km=1.5,
        base_travel_minutes=3.0,
    )

    city.add_bidirectional_road(
        "B",
        "C",
        distance_km=1.0,
        base_travel_minutes=2.0,
    )

    city.add_bidirectional_road(
        "A",
        "D",
        distance_km=2.0,
        base_travel_minutes=4.0,
    )

    city.add_bidirectional_road(
        "D",
        "C",
        distance_km=1.0,
        base_travel_minutes=2.0,
    )

    city.add_bidirectional_road(
        "C",
        "E",
        distance_km=2.0,
        base_travel_minutes=4.0,
    )

    city.add_bidirectional_road(
        "DEPOT",
        "D",
        distance_km=3.5,
        base_travel_minutes=8.0,
    )

    city.add_bidirectional_road(
        "D",
        "CHARGER_1",
        distance_km=1.5,
        base_travel_minutes=3.0,
    )

    city.add_bidirectional_road(
        "E",
        "CHARGER_1",
        distance_km=2.5,
        base_travel_minutes=5.0,
    )

    return city