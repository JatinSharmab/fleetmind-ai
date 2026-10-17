import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import health, simulation
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.postgres import PostgresManager
from app.db.redis import RedisManager
from app.events.publisher import RedisEventPublisher
from app.simulator.exceptions import SimulationError


settings = get_settings()

configure_logging(
    settings.log_level
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    postgres = PostgresManager(
        settings.postgres_dsn
    )

    redis = RedisManager(
        settings.redis_url
    )

    logger.info(
        "fleetmind_starting",
        extra={
            "environment": settings.environment,
        },
    )

    try:
        await postgres.connect()
        await redis.connect()

        app.state.postgres = postgres
        app.state.redis = redis

        app.state.event_publisher = (
            RedisEventPublisher(
                redis_client=redis.client,
                stream_name=(
                    settings.redis_event_stream
                ),
            )
        )

        logger.info(
            "fleetmind_infrastructure_ready",
            extra={
                "environment": (
                    settings.environment
                )
            },
        )

        yield

    finally:
        await redis.disconnect()
        await postgres.disconnect()

        logger.info(
            "fleetmind_shutdown_complete"
        )


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(
        health.router
    )

    app.include_router(
        simulation.router
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "phase": "1",
            "architecture": "Digital Twin Foundation",
        }

    @app.exception_handler(
        SimulationError
    )
    async def simulation_exception_handler(
        _request: Request,
        exc: SimulationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": exc.__class__.__name__,
                "detail": str(exc),
            },
        )

    return app


app = create_app()