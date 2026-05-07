"""Pydantic schemas for classify (pollution scene, not SKU-level litter)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ClassificationPrediction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pollutant_kind: str = Field(
        ...,
        serialization_alias="class",
        description=(
            "BR-REP-005 scene category: TRASH / WATER / SMOKE / CHEMICAL "
            "(detector aggregates; tiếng ồn do user nhập)."
        ),
    )

    confidence: float = Field(ge=0.0, le=1.0)

    bbox_count: int = Field(
        ge=0,
        description="Số bbox góp vào chứng cứ của loại ô nhiễm (không phải SKU từng món).",
    )


class ClassifyRequest(BaseModel):
    image_url: str = Field(description="Fetchable URI (HTTP(S), s3://, or file:// for tests).")


ImageRelevance = Literal[
    "POLLUTION_LIKELY",
    "NOT_POLLUTION_OR_UNRELATED",
    "UNCLEAR_NEED_MANUAL_REVIEW",
]

SeverityBand = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


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

    model_version: str

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
