"""Pydantic schemas for dataset upload and training jobs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    created_at: str
    summary: dict


class CreateTrainingJobRequest(BaseModel):
    dataset_id: str
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


class TrainingLogResponse(BaseModel):
    content: str
    next_offset: int
    eof: bool
    total_size: int | None = None
    status: str | None = None
