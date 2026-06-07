"""Pydantic schemas for dataset upload and training jobs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    created_at: str
    summary: dict


class CreateTrainingJobRequest(BaseModel):
    dataset_id: str = Field(
        default="", description="Single dataset ID. Ignored khi dataset_ids có >= 2 phần tử."
    )
    dataset_ids: list[str] | None = Field(
        default=None,
        description="Danh sách dataset_id để gộp lại trước khi train. Ưu tiên cao hơn dataset_id.",
    )
    run_name: str = Field(default="pollution_detect")
    epochs: int = Field(default=50, ge=1, le=1000)
    batch: int = Field(default=16, ge=1, le=1024)
    imgsz: int = Field(default=640, ge=128, le=4096)
    model_path: str | None = Field(
        default=None,
        description="Optional explicit checkpoint path. Leave empty to auto-resume.",
    )
    continue_from_latest: bool = Field(
        default=True,
        description="When model_path is empty, continue from latest SUCCEEDED training job.",
    )
    continue_from_job_id: str | None = Field(
        default=None,
        description="Optional source training job id to continue from (takes highest priority).",
    )
    enable_wandb: bool = Field(default=False)
    wandb_project: str | None = None
    wandb_entity: str | None = None
    wandb_api_key: str | None = Field(
        default=None,
        description="Optional runtime key; prefer setting env WANDB_API_KEY on local machine.",
    )


class MergeDatasetsRequest(BaseModel):
    dataset_ids: list[str] = Field(
        min_length=2,
        description="Danh sách dataset_id cần gộp (tối thiểu 2).",
    )


class TrainingJobListResponse(BaseModel):
    items: list[TrainingJobResponse]
    total: int
    limit: int
    offset: int


class SceneTrainingJobListResponse(BaseModel):
    items: list[SceneTrainingJobResponse]
    total: int
    limit: int
    offset: int


class TrainingJobResponse(BaseModel):
    job_id: str
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]
    dataset_id: str
    run_name: str
    created_at: str
    updated_at: str
    epochs: int
    batch: int
    imgsz: int
    model_path: str
    result: dict | None = None
    error_text: str | None = None
    metrics: dict | None = None
    log_size_bytes: int | None = None
    dataset_summary: dict | None = None


class TrainingLogResponse(BaseModel):
    content: str
    next_offset: int
    eof: bool
    total_size: int | None = None
    status: str | None = None


# --- Dataset inspect / convert schemas ---


class DatasetInspectResponse(BaseModel):
    yaml_file: str | None
    detected_classes: dict[int, str]
    target_classes: dict[int, str]


class DatasetConvertRequest(BaseModel):
    mapping: dict[str, str] = Field(
        description='Map source class name or int id (as str) to target: {"Plastic Trash": "TRASH"}'
    )


# --- Scene Classifier training schemas ---


class SceneDatasetUploadResponse(BaseModel):
    dataset_id: str
    created_at: str
    summary: dict


class CreateSceneTrainingJobRequest(BaseModel):
    dataset_id: str
    run_name: str = Field(default="scene_classifier")
    epochs: int = Field(default=15, ge=1, le=1000)
    batch: int = Field(default=16, ge=1, le=512)
    lr: float = Field(default=1e-4, gt=0.0, le=1.0)
    output_path: str | None = Field(
        default=None,
        description="Where to save best.pt. Defaults to ml/weights/scene_classifier.pt.",
    )


class SceneTrainingJobResponse(BaseModel):
    job_id: str
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]
    dataset_id: str
    run_name: str
    created_at: str
    updated_at: str
    epochs: int
    batch: int
    lr: float
    data_root: str
    output_path: str
    result: dict | None = None
    error_text: str | None = None
    log_size_bytes: int | None = None
    dataset_summary: dict | None = None


# --- Trash subtype classifier training schemas ---


class SubtypeDatasetUploadResponse(BaseModel):
    dataset_id: str
    created_at: str
    summary: dict


class CreateSubtypeTrainingJobRequest(BaseModel):
    dataset_id: str
    run_name: str = Field(default="trash_subtype_classifier")
    epochs: int = Field(default=100, ge=1, le=1000)
    batch: int = Field(default=32, ge=1, le=512)
    lr: float = Field(default=0.001, gt=0.0, le=1.0)
    output_path: str | None = Field(
        default=None,
        description="Where to save weights. Defaults to ml/weights/trash_subtype_classifier.pt.",
    )


class SubtypeTrainingJobResponse(BaseModel):
    job_id: str
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]
    dataset_id: str
    run_name: str
    created_at: str
    updated_at: str
    epochs: int
    batch: int
    lr: float
    data_root: str
    output_path: str
    result: dict | None = None
    error_text: str | None = None
    log_size_bytes: int | None = None
    dataset_summary: dict | None = None


class SubtypeTrainingJobListResponse(BaseModel):
    items: list[SubtypeTrainingJobResponse]
    total: int
    limit: int
    offset: int
