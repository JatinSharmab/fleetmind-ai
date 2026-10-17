import pytest

from app.simulator.city import build_demo_city
from app.simulator.exceptions import RouteUnavailableError


def test_shortest_route_exists() -> None:
    city = build_demo_city()

    route = city.shortest_route(
        "DEPOT",
        "B",
    )

    assert route.nodes == [
        "DEPOT",
        "A",
        "B",
    ]

    assert route.distance_km == 3.5
    assert route.travel_minutes == 7.0


def test_blocked_road_is_avoided() -> None:
    city = build_demo_city()

    city.set_road_blocked(
        "A",
        "B",
        True,
    )

    route = city.shortest_route(
        "DEPOT",
        "C",
    )

    edges = list(
        zip(
            route.nodes,
            route.nodes[1:],
            strict=False,
        )
    )

    assert ("A", "B") not in edges


def test_unreachable_destination_raises() -> None:
    city = build_demo_city()

    city.set_road_blocked(
        "DEPOT",
        "A",
        True,
    )

    city.set_road_blocked(
        "DEPOT",
        "D",
        True,
    )

    with pytest.raises(
        RouteUnavailableError
    ):
        city.shortest_route(
            "DEPOT",
            "B",
        )