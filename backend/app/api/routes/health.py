from fastapi import APIRouter, HTTPException, Request


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {
        "status": "alive",
    }


@router.get("/ready")
async def readiness(
    request: Request,
) -> dict:
    postgres_ok = (
        await request.app.state.postgres.ping()
    )

    redis_ok = (
        await request.app.state.redis.ping()
    )

    if not postgres_ok or not redis_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "postgres": postgres_ok,
                "redis": redis_ok,
            },
        )

    return {
        "status": "ready",
        "postgres": True,
        "redis": True,
    }