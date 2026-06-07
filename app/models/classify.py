"""Pydantic schemas for classify (pollution scene, not SKU-level litter)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DetectedBox(BaseModel):
    """Tọa độ pixel của một bounding box (absolute, xyxy format)."""

    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = Field(ge=0.0, le=1.0)
    subtype: str | None = Field(
        default=None, description="Trash subtype for this box (TRASH class only)."
    )
    subtype_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class TrashSubtypePrediction(BaseModel):
    """Aggregated trash subtype count across all boxes in one TRASH prediction."""

    subtype: str
    count: int = Field(ge=0, description="Number of boxes classified as this subtype.")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Best confidence among boxes of this subtype."
    )


class ClassificationPrediction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pollutant_kind: str = Field(
        ...,
        serialization_alias="class",
        description=(
            "BR-REP-005 scene category: TRASH / WATER "
            "(detector aggregates; tiếng ồn do user nhập)."
        ),
    )

    confidence: float = Field(ge=0.0, le=1.0)

    bbox_count: int = Field(
        ge=0,
        description="Số bbox góp vào chứng cứ của loại ô nhiễm (không phải SKU từng món).",
    )

    boxes: list[DetectedBox] = Field(
        default_factory=list,
        description="Tọa độ pixel (xyxy) của từng bounding box thuộc loại ô nhiễm này.",
    )

    subtypes: list[TrashSubtypePrediction] | None = Field(
        default=None,
        description="Trash subtype breakdown — only present when class=TRASH and subtype model is active.",
    )


class ClassifyRequest(BaseModel):
    image_url: str = Field(description="Fetchable URI (HTTP(S), s3://, or file:// for tests).")


ImageRelevance = Literal[
    "POLLUTION_LIKELY",
    "NOT_POLLUTION_OR_UNRELATED",
    "UNCLEAR_NEED_MANUAL_REVIEW",
]

SeverityBand = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
ReportImageDecision = Literal[
    "ACCEPTABLE_REPORT_IMAGE",
    "NEED_MANUAL_REVIEW",
    "IRRELEVANT_OR_SUSPECTED_ABUSIVE",
]


class ClassifyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    predictions: list[ClassificationPrediction] = Field(
        default_factory=list,
        description="Chứng cứ theo từng loại ô nhiễm (gom từ cảnh, không nhắm SKU rác chi tiết).",
    )

    primary_class: str | None = Field(
        default=None,
        description="Loại ô nhiễm nổi bật nhất trong ảnh (business label).",
    )

    confidence: float = Field(ge=0.0, le=1.0)

    action: Literal["AUTO_FILL", "SUGGEST", "KEEP_USER_CHOICE"]

    model_version: str = Field(
        description=(
            "Composite audit string: YOLO version and scene status, e.g. "
            "'v1.4.0-yolo|scene:v1.0.0-scene' or 'v1.4.0-yolo|scene:off'."
        ),
    )

    yolo_active: bool = Field(
        description="True when YOLO detector weights were loaded and used for this request.",
    )

    scene_classifier_active: bool = Field(
        description="True when scene classifier weights were loaded and ran for this request.",
    )

    trash_subtype_active: bool = Field(
        default=False,
        description="True when trash subtype classifier was loaded and ran for this request.",
    )

    detector_model_version: str | None = Field(
        default=None,
        description="MODEL_VERSION from settings when YOLO is active; null when YOLO is off.",
    )

    scene_model_version: str | None = Field(
        default=None,
        description="SCENE_CLASSIFIER_VERSION when scene model is active; null when scene is off.",
    )

    scene_scores: dict[str, float] | None = Field(
        default=None,
        description="WATER probability from scene classifier when active.",
    )

    inference_time_ms: float = Field(ge=0.0)

    noise_supported: bool = Field(
        default=False,
        description="False — tiếng ồn không infer từ ảnh (Option A).",
    )

    severity: SeverityBand = Field(
        ...,
        description="Mức độ ô nhiễm trong ảnh (BR-AI-003 v1: từ tỷ lệ vùng nhận dạng / diện tích ảnh).",
    )

    pollution_coverage_ratio: float = Field(
        ...,
        ge=0.0,
        description="Tổng diện tích bbox (đã map loại ô nhiễm) / diện tích ảnh, clamp ≤ 1.",
    )

    image_relevance: ImageRelevance = Field(
        ...,
        description=(
            "Ảnh có phải cảnh báo cáo ô nhiễm thuyết phục không, hay nghi không liên quan / cần người xem."
        ),
    )


class ClassifyModerationResponse(BaseModel):
    decision: ReportImageDecision
    reason: str
    classify: ClassifyResponse
