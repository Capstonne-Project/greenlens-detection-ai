"""BR-REP-030 / BR-AI-002 — Tier 2 duplicate detection via DINOv2 image compare."""

from __future__ import annotations

import asyncio
import time
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.deps import get_image_compare_cached
from app.config import get_settings
from app.core.image_compare import CompareResult, ImageCompareService
from app.models.compare import CompareRequest, CompareResponse
from app.services import storage_service
from app.utils.image_decode import HeifDecoderUnavailableError, normalize_classify_image_bytes
from app.utils.logger import get_logger

router = APIRouter(tags=["compare"])

_MAX_COMPARE_BYTES = 100 * 1024 * 1024


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


async def _read_upload_file(upload: UploadFile, label: str) -> bytes:
    payload = await upload.read()
    if not payload:
        raise HTTPException(status_code=400, detail=f"Empty upload: {label}.")
    if len(payload) > _MAX_COMPARE_BYTES:
        raise HTTPException(status_code=413, detail=f"Image too large: {label}.")
    try:
        return normalize_classify_image_bytes(payload, upload.filename)
    except HeifDecoderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{label}: {exc}") from exc


def _run_compare(svc: ImageCompareService, blob_a: bytes, blob_b: bytes) -> CompareResult:
    try:
        return svc.compare_bytes(blob_a, blob_b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected inference failure
        raise HTTPException(status_code=500, detail=f"Compare failed: {exc}") from exc


def _to_response(result: CompareResult, elapsed_ms: int) -> CompareResponse:
    return CompareResponse(
        confidence=result.confidence,
        is_same_scene=result.is_same_scene,
        model=result.model,
        processing_time_ms=elapsed_ms,
    )


def _log_compare(logger, result: CompareResult, elapsed_ms: int) -> None:
    logger.info(
        "compare_images",
        confidence=result.confidence,
        is_same_scene=result.is_same_scene,
        model=result.model,
        processing_ms=elapsed_ms,
    )


@router.post(
    "/compare-images",
    response_model=CompareResponse,
    summary="So sánh 2 ảnh qua URL (DINOv2) — dùng cho .NET",
)
async def compare_images(body: CompareRequest) -> CompareResponse:
    """JSON body với image_url_a / image_url_b — .NET gọi sau Tier 1."""
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

    result = await asyncio.to_thread(_run_compare, svc, blob_a, blob_b)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    _log_compare(logger, result, elapsed_ms)
    return _to_response(result, elapsed_ms)


@router.post(
    "/compare-images-upload",
    response_model=CompareResponse,
    summary="So sánh 2 ảnh upload (multipart) — test local / Swagger",
)
async def compare_images_upload(
    image_a: Annotated[
        UploadFile,
        File(description="Ảnh báo cáo mới (JPEG/PNG/HEIC)."),
    ],
    image_b: Annotated[
        UploadFile,
        File(description="Ảnh báo cáo candidate (JPEG/PNG/HEIC)."),
    ],
) -> CompareResponse:
    """multipart/form-data — tải 2 file từ máy, không cần URL."""
    logger = get_logger(__name__)
    svc = get_image_compare_cached()

    if not svc.model_is_loaded():
        raise HTTPException(
            status_code=503,
            detail="DINOv2 compare model is not available.",
        )

    start = time.perf_counter()
    blob_a, blob_b = await asyncio.gather(
        _read_upload_file(image_a, "image_a"),
        _read_upload_file(image_b, "image_b"),
    )

    result = await asyncio.to_thread(_run_compare, svc, blob_a, blob_b)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    _log_compare(logger, result, elapsed_ms)
    return _to_response(result, elapsed_ms)
