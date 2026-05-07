"""BR-AI-001 / BR-AI-003 — pollution scene classify + relevance + severity."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.deps import get_pollution_classifier_cached
from app.models.classify import ClassificationPrediction, ClassifyRequest, ClassifyResponse
from app.services import storage_service
from app.utils.logger import get_logger

router = APIRouter(tags=["classification"])


_MAX_CLASSIFY_BYTES = 20 * 1024 * 1024


def classify_image_bytes_to_response(image_bytes: bytes) -> ClassifyResponse:
    clf = get_pollution_classifier_cached()

    result = clf.classify_bytes(image_bytes)

    preds = [
        ClassificationPrediction(
            pollutant_kind=p["class"],
            confidence=float(p["confidence"]),
            bbox_count=int(p["bbox_count"]),
        )
        for p in result.predictions
    ]

    return ClassifyResponse(
        predictions=preds,
        primary_class=result.primary_class,
        confidence=float(result.confidence),
        action=result.action,  # type: ignore[arg-type]
        model_version=result.model_version,
        inference_time_ms=result.inference_time_ms,
        noise_supported=result.noise_supported,
        severity=result.severity,  # type: ignore[arg-type]
        pollution_coverage_ratio=float(result.pollution_coverage_ratio),
        image_relevance=result.image_relevance,  # type: ignore[arg-type]
    )


def _log_classify(logger, response: ClassifyResponse) -> None:
    logger.info(
        "classify",
        prediction_count=len(response.predictions),
        action=response.action,
        inference_ms=response.inference_time_ms,
        model_version=response.model_version,
        severity=response.severity,
        image_relevance=response.image_relevance,
        coverage=response.pollution_coverage_ratio,
    )


@router.post(
    "/classify",
    response_model=ClassifyResponse,
    response_model_by_alias=True,
)
async def classify(body: ClassifyRequest) -> ClassifyResponse:
    logger = get_logger(__name__)

    blob = await storage_service.fetch_image_bytes(body.image_url)

    if len(blob) > _MAX_CLASSIFY_BYTES:
        raise HTTPException(status_code=413, detail="Image too large.")

    response = classify_image_bytes_to_response(blob)

    _log_classify(logger, response)

    return response


@router.post(
    "/classify-upload",
    response_model=ClassifyResponse,
    response_model_by_alias=True,
    summary="Classify from captured/uploaded image (multipart)",
    description=(
        "Same contract as /classify — pollution types, relevance, severity; "
        "not fine-grained waste SKU tagging."
    ),
)
async def classify_upload(
    image: Annotated[
        UploadFile,
        File(description="Camera capture or gallery file (JPEG/PNG recommended)."),
    ],
) -> ClassifyResponse:
    logger = get_logger(__name__)

    payload = await image.read()

    if not payload:
        raise HTTPException(status_code=400, detail="Empty upload.")

    if len(payload) > _MAX_CLASSIFY_BYTES:
        raise HTTPException(status_code=413, detail="Image too large.")

    response = classify_image_bytes_to_response(payload)

    _log_classify(logger, response)

    return response
