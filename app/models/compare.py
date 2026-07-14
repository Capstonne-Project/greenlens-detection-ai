"""Pydantic schemas for /compare-images (DINOv2 Tier 2 duplicate detection)."""

from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    image_url_a: str = Field(
        description="Ảnh báo cáo MỚI. Fetchable URI (HTTP(S), s3://, hoặc file:// cho test).",
    )
    image_url_b: str = Field(
        description="Ảnh báo cáo CANDIDATE đã tồn tại. Fetchable URI.",
    )


class CompareResponse(BaseModel):
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Độ tin cậy cùng cảnh (cosine similarity embeddings DINOv2 [CLS], L2-normalized).",
    )
    is_same_scene: bool = Field(
        description="True khi confidence >= COMPARE_THRESHOLD (mặc định 0.80).",
    )
    model: str = Field(
        description="Nhãn model dùng để so sánh (BR-AI-005 audit), ví dụ 'dinov2-base'.",
    )
    processing_time_ms: int = Field(
        ge=0,
        description="Tổng thời gian xử lý phía AI service (ms).",
    )
