"""Health and readiness endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — service is alive."""
    return HealthResponse(status="ok", service="ai-service")


@router.get("/ready", response_model=HealthResponse)
async def ready() -> HealthResponse:
    """Readiness probe — service is ready to accept traffic.

    TODO Phase 3+: check model loaded, redis connected, S3 reachable.
    """
    return HealthResponse(status="ready", service="ai-service")
