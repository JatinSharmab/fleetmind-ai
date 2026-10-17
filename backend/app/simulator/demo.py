import asyncio

from app.events.publisher import InMemoryEventPublisher
from app.simulator.factory import build_demo_mission


async def main() -> None:
    publisher = InMemoryEventPublisher()

    runner, mission = build_demo_mission(
        publisher
    )

    result = await runner.run(mission)

    print(
        result.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    asyncio.run(main())