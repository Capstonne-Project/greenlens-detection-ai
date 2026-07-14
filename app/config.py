"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # App
    app_name: str = "ai-service"
    app_env: str = "development"
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "ai-service"

    # AI
    model_path: str = "ml/weights/yolov8n.pt"  # missing file -> classify stub mode (CI)
    model_version: str = "v0.1.0-yolov8n"  # BR-AI-005 audit string on classify
    inference_timeout_seconds: float = 4.5

    classification_confidence_auto: float = 0.8
    classification_confidence_suggest_low: float = 0.5

    # Severity (BR-AI-003 v1): polluted bbox area sum / image area — band upper edges
    severity_cover_low_below: float = 0.05
    severity_cover_medium_below: float = 0.15
    severity_cover_high_below: float = 0.40

    # Mapped pollution box confidence floor for POLLUTION_LIKELY
    relevance_min_confidence: float = 0.3

    suspicious_edit_time_diff_hours: float = 1.0
    duplicate_phash_similarity_threshold: float = 0.85
    duplicate_max_distance_meters: float = 50.0
    duplicate_max_time_diff_hours: float = 24.0

    # True -> no S3 upload; return placeholder stripped_image_url (local dev)
    storage_stub_mode: bool = True

    # Local UI only: when weights file missing, return a fake SUGGEST row (BR-AI-001 demo).
    classify_demo_mode: bool = False

    # Scene classifier (EfficientNet-B0) — empty string disables it
    scene_classifier_path: str = ""
    scene_classifier_version: str = ""  # BR-AI-005 audit label when scene weights are loaded
    scene_classifier_threshold: float = 0.45

    # Trash subtype classifier (EfficientNet-B0) — empty string disables it
    trash_subtype_model_path: str = ""
    trash_subtype_threshold: float = 0.40  # min confidence to report a subtype (vs UNKNOWN)

    # ── Image compare (DINOv2) — BR-REP-030/BR-AI-002 Tier 2 duplicate detection ──
    compare_model_name: str = Field(
        default="facebook/dinov2-base",
        validation_alias="COMPARE_MODEL_NAME",
        description="HuggingFace model id (e.g. facebook/dinov2-base, facebook/dinov2-small).",
    )
    compare_model_version: str = Field(
        default="dinov2-base",
        validation_alias="COMPARE_MODEL_VERSION",
        description="Returned as `model` in API response (BR-AI-005 audit).",
    )
    compare_threshold: float = Field(
        default=0.80,
        validation_alias="COMPARE_THRESHOLD",
        description="confidence >= threshold → is_same_scene.",
    )
    compare_download_timeout_seconds: float = Field(
        default=3.0,
        validation_alias="COMPARE_DOWNLOAD_TIMEOUT_SECONDS",
        description="Per-image URL fetch timeout for POST /compare-images.",
    )
    compare_warmup_on_startup: bool = Field(
        default=False,
        validation_alias="COMPARE_WARMUP_ON_STARTUP",
        description="Preload DINOv2 in lifespan (recommended on prod).",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
