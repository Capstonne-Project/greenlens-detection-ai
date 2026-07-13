"""BR-REP-030 / BR-AI-002 — Tier 2 duplicate detection via DINOv2 image compare."""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, HTTPException

from app.api.deps import get_image_compare_cached
from app.config import get_settings
from app.core.image_compare import CompareResult
from app.models.compare import CompareRequest, CompareResponse
from app.services import storage_service
from app.utils.logger import get_logger

router = APIRouter(tags=["compare"])


async def _fetch_with_timeout(url: str, timeout: float, label: str) -> bytes:
    try:
        return await asyncio.wait_for(storage_service.fetch_image_bytes(url), timeout=timeout)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Timeout downloading {label}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to download {label}: {exc}",
        ) from exc


@router.post(
    "/compare-images",
    response_model=CompareResponse,
    summary="So sánh 2 ảnh (DINOv2) — Tier 2 duplicate detection",
)
async def compare_images(body: CompareRequest) -> CompareResponse:
    logger = get_logger(__name__)
    settings = get_settings()
    svc = get_image_compare_cached()

    if not svc.model_is_loaded():
        raise HTTPException(
            status_code=503,
            detail="DINOv2 compare model is not available.",
        )

    start = time.perf_counter()

    timeout = settings.compare_download_timeout_seconds
    blob_a, blob_b = await asyncio.gather(
        _fetch_with_timeout(body.image_url_a, timeout, "image_url_a"),
        _fetch_with_timeout(body.image_url_b, timeout, "image_url_b"),
    )

    try:
        result: CompareResult = await asyncio.to_thread(svc.compare_bytes, blob_a, blob_b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected inference failure
        raise HTTPException(status_code=500, detail=f"Compare failed: {exc}") from exc

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    logger.info(
        "compare_images",
        similarity=result.similarity,
        is_same_scene=result.is_same_scene,
        model=result.model,
        processing_ms=elapsed_ms,
    )

    return CompareResponse(
        similarity=result.similarity,
        is_same_scene=result.is_same_scene,
        model=result.model,
        processing_time_ms=elapsed_ms,
    )
