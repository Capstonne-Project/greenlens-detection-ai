"""Dataset upload + local training orchestration APIs for dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.training_jobs import get_training_orchestrator
from app.models.training import (
    CreateTrainingJobRequest,
    DatasetUploadResponse,
    TrainingJobResponse,
    TrainingLogResponse,
)

router = APIRouter(prefix="/training", tags=["training"])


@router.post("/datasets/upload", response_model=DatasetUploadResponse)
async def upload_dataset_zip(
    dataset_zip: Annotated[
        UploadFile,
        File(description="Zip with YOLO folders images/train,val + labels/train,val."),
    ],
) -> DatasetUploadResponse:
    blob = await dataset_zip.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty dataset zip.")
    if not dataset_zip.filename:
        raise HTTPException(status_code=400, detail="Dataset filename is required.")
    orchestrator = get_training_orchestrator()
    try:
        payload = orchestrator.upload_dataset(filename=dataset_zip.filename, content=blob)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DatasetUploadResponse(
        dataset_id=payload["dataset_id"],
        created_at=payload["created_at"],
        summary=payload["summary"],
    )


@router.post("/jobs", response_model=TrainingJobResponse)
async def create_training_job(body: CreateTrainingJobRequest) -> TrainingJobResponse:
    orchestrator = get_training_orchestrator()
    try:
        payload = orchestrator.create_job(
            dataset_id=body.dataset_id,
            run_name=body.run_name,
            epochs=body.epochs,
            batch=body.batch,
            imgsz=body.imgsz,
            model_path=body.model_path,
            continue_from_latest=body.continue_from_latest,
            continue_from_job_id=body.continue_from_job_id,
            enable_wandb=body.enable_wandb,
            wandb_project=body.wandb_project,
            wandb_entity=body.wandb_entity,
            wandb_api_key=body.wandb_api_key,
        )
        detail = orchestrator.get_job(payload["job_id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainingJobResponse(**detail)


@router.get("/jobs", response_model=list[TrainingJobResponse])
async def list_training_jobs() -> list[TrainingJobResponse]:
    orchestrator = get_training_orchestrator()
    return [TrainingJobResponse(**job) for job in orchestrator.list_jobs()]


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(job_id: str) -> TrainingJobResponse:
    orchestrator = get_training_orchestrator()
    try:
        payload = orchestrator.get_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TrainingJobResponse(**payload)


@router.get("/jobs/{job_id}/logs", response_model=TrainingLogResponse)
async def get_training_job_logs(
    job_id: str,
    offset: int = 0,
    limit: int = 20000,
) -> TrainingLogResponse:
    orchestrator = get_training_orchestrator()
    try:
        payload = orchestrator.read_log(job_id, offset=offset, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TrainingLogResponse(**payload)
