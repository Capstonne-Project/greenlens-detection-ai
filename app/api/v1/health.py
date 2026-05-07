"""Health and readiness endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import get_pollution_classifier_cached

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str


class ReadyResponse(HealthResponse):
    model_loaded: bool = Field(
        description="True when YOLO weights exist at configured model_path and loaded.",
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — service is alive."""
    return HealthResponse(status="ok", service="ai-service")


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    """Readiness probe — process can serve traffic; optional model warmup."""
    clf = get_pollution_classifier_cached()
    loaded = clf.model_is_loaded()
    return ReadyResponse(status="ready", service="ai-service", model_loaded=loaded)
