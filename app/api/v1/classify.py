"""BR-AI-001 / BR-AI-003 — pollution scene classify + relevance + severity."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.deps import get_pollution_classifier_cached
from app.models.classify import (
    ClassificationPrediction,
    ClassifyModerationResponse,
    ClassifyRequest,
    ClassifyResponse,
    DetectedBox,
    TrashSubtypePrediction,
)
from app.services import storage_service
from app.utils.image_decode import HeifDecoderUnavailableError, normalize_classify_image_bytes
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
            boxes=[DetectedBox(**b) for b in p.get("boxes", [])],
            subtypes=(
                [TrashSubtypePrediction(**s) for s in p["subtypes"]] if p.get("subtypes") else None
            ),
        )
        for p in result.predictions
    ]

    return ClassifyResponse(
        predictions=preds,
        primary_class=result.primary_class,
        confidence=float(result.confidence),
        action=result.action,  # type: ignore[arg-type]
        model_version=result.model_version,
        yolo_active=result.yolo_active,
        scene_classifier_active=result.scene_classifier_active,
        trash_subtype_active=result.trash_subtype_active,
        detector_model_version=result.detector_model_version,
        scene_model_version=result.scene_model_version,
        scene_scores=result.scene_scores,
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
        yolo_active=response.yolo_active,
        scene_classifier_active=response.scene_classifier_active,
        severity=response.severity,
        image_relevance=response.image_relevance,
        coverage=response.pollution_coverage_ratio,
    )


def _moderation_from_classify(response: ClassifyResponse) -> tuple[str, str]:
    if response.image_relevance == "POLLUTION_LIKELY":
        return (
            "ACCEPTABLE_REPORT_IMAGE",
            "Mapped pollution evidence is strong enough for report workflow.",
        )
    if response.image_relevance == "UNCLEAR_NEED_MANUAL_REVIEW":
        return (
            "NEED_MANUAL_REVIEW",
            "Image has low-confidence or unmapped objects; require manual review.",
        )
    return (
        "IRRELEVANT_OR_SUSPECTED_ABUSIVE",
        "No mapped pollution evidence; likely irrelevant upload or suspicious content.",
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

    try:
        payload = normalize_classify_image_bytes(payload, image.filename)
    except HeifDecoderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = classify_image_bytes_to_response(payload)

    _log_classify(logger, response)

    return response


@router.post(
    "/classify-moderation-upload",
    response_model=ClassifyModerationResponse,
    response_model_by_alias=True,
    summary="Classify pollution + report-image moderation decision",
)
async def classify_moderation_upload(
    image: Annotated[
        UploadFile,
        File(description="Camera capture or gallery file for moderation-aware classify."),
    ],
) -> ClassifyModerationResponse:
    response = await classify_upload(image)
    decision, reason = _moderation_from_classify(response)
    return ClassifyModerationResponse(decision=decision, reason=reason, classify=response)
