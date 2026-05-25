"""Dataset upload + local training orchestration APIs for dashboard."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile

from app.core.training_jobs import (
    convert_dataset_zip,
    filter_classes_zip,
    get_scene_training_orchestrator,
    get_training_orchestrator,
    inspect_dataset_zip,
    merge_zips_direct,
    restructure_dataset_zip,
    split_dataset_zip,
)
from app.models.training import (
    CreateSceneTrainingJobRequest,
    CreateTrainingJobRequest,
    DatasetInspectResponse,
    DatasetUploadResponse,
    MergeDatasetsRequest,
    SceneDatasetUploadResponse,
    SceneTrainingJobListResponse,
    SceneTrainingJobResponse,
    TrainingJobListResponse,
    TrainingJobResponse,
    TrainingLogResponse,
)

router = APIRouter(prefix="/training", tags=["training"])


@router.post("/datasets/split")
async def split_dataset(
    dataset_zip: Annotated[
        UploadFile,
        File(
            description="YOLO ZIP with images + labels. Image/label pairs are matched by filename stem."
        ),
    ],
    split_count: int = 1,
) -> Response:
    """Split a dataset ZIP into two ZIPs (split + remainder), both returned inside a wrapper ZIP."""
    blob = await dataset_zip.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty zip.")
    if split_count < 1:
        raise HTTPException(status_code=400, detail="split_count must be >= 1.")
    try:
        split_zip, remainder_zip, stats = split_dataset_zip(blob, split_count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    base_name = (dataset_zip.filename or "dataset").removesuffix(".zip")

    # Bundle both ZIPs into a single wrapper ZIP for one-click download
    bundle_buf = io.BytesIO()
    with zipfile.ZipFile(bundle_buf, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(f"{base_name}_split_{stats['split_images']}.zip", split_zip)
        bundle.writestr(f"{base_name}_remainder_{stats['remainder_images']}.zip", remainder_zip)

    return Response(
        content=bundle_buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{base_name}_split_bundle.zip"',
            "X-Stats": json.dumps(stats),
        },
    )


@router.post("/datasets/filter-classes")
async def filter_dataset_classes(
    dataset_zip: Annotated[
        UploadFile,
        File(description="YOLO ZIP. Images+labels for unwanted class IDs are removed entirely."),
    ],
    keep_ids_json: Annotated[
        str,
        Form(description="JSON array of class IDs to KEEP, e.g. [0, 2]. All others are dropped."),
    ],
) -> Response:
    """Drop images whose labels contain only unwanted classes; rewrite yaml with new class list."""
    blob = await dataset_zip.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty zip.")
    try:
        keep_ids: list[int] = json.loads(keep_ids_json)
        if not isinstance(keep_ids, list) or not keep_ids:
            raise ValueError("keep_ids_json must be a non-empty JSON array of integers.")
        keep_set = {int(x) for x in keep_ids}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"keep_ids_json invalid: {exc}") from exc
    try:
        out_bytes, stats = filter_classes_zip(blob, keep_set)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    base_name = (dataset_zip.filename or "dataset").removesuffix(".zip")
    return Response(
        content=out_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{base_name}_filtered.zip"',
            "X-Stats": json.dumps(stats),
        },
    )


@router.post("/datasets/restructure")
async def restructure_dataset(
    dataset_zip: Annotated[
        UploadFile,
        File(
            description="ZIP with train/<imgs> + labels/<txts>. Converts to images/train,val + labels/train,val."
        ),
    ],
    val_fraction: float = 0.15,
) -> Response:
    blob = await dataset_zip.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty zip.")
    if not (0.0 < val_fraction < 1.0):
        raise HTTPException(status_code=400, detail="val_fraction must be between 0 and 1.")
    try:
        out_bytes, stats = restructure_dataset_zip(blob, val_fraction=val_fraction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    filename = (dataset_zip.filename or "dataset").removesuffix(".zip") + "_structured.zip"
    return Response(
        content=out_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Stats": json.dumps(stats),
        },
    )


@router.post("/datasets/inspect", response_model=DatasetInspectResponse)
async def inspect_dataset(
    dataset_zip: Annotated[
        UploadFile,
        File(description="Any YOLO ZIP — returns detected class names from data.yaml."),
    ],
) -> DatasetInspectResponse:
    blob = await dataset_zip.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty zip.")
    try:
        info = inspect_dataset_zip(blob)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DatasetInspectResponse(**info)


@router.post("/datasets/preview-labels")
async def preview_labels(
    dataset_zip: Annotated[UploadFile, File(description="YOLO ZIP to preview.")],
    target_class: Annotated[
        str, Form(description="TRASH|WATER|SMOKE — class_id sẽ remap về")
    ] = "TRASH",
) -> Response:
    """Đọc ZIP server-side, trả JSON: image_count, label_count, label_format, sample_lines (sau remap)."""
    blob = await dataset_zip.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty zip.")

    target_ids = {"TRASH": 0, "WATER": 1, "SMOKE": 2}
    target_class = target_class.strip().upper()
    if target_class not in target_ids:
        raise HTTPException(status_code=400, detail="target_class phải là TRASH, WATER hoặc SMOKE.")
    new_id = target_ids[target_class]

    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}
    img_count = 0
    label_count = 0
    sample_lines: list[str] = []
    col_counts: list[int] = []

    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            for info in zf.infolist():
                name = info.filename
                if name.startswith("__MACOSX") or name.endswith("/"):
                    continue
                ext = Path(name).suffix.lower()
                if ext in image_exts:
                    img_count += 1
                elif ext == ".txt" and Path(name).name not in ("requirements.txt", "README.txt"):
                    label_count += 1
                    if len(sample_lines) < 6:
                        try:
                            raw = zf.read(name).decode("utf-8", errors="replace")
                            for line in raw.strip().splitlines()[:2]:
                                parts = line.strip().split()
                                if len(parts) >= 5:
                                    col_counts.append(len(parts))
                                    # remap class_id
                                    parts[0] = str(new_id)
                                    sample_lines.append(" ".join(parts))
                        except Exception:
                            pass
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Lỗi đọc ZIP: {exc}") from exc

    # Detect format
    avg_cols = sum(col_counts) / len(col_counts) if col_counts else 0
    if avg_cols >= 8:
        label_fmt = "OBB"
        fmt_note = "⚠️ OBB format (8–9 cột) — sẽ tự động convert sang AABB khi gộp"
    elif 4 < avg_cols <= 5:
        label_fmt = "AABB"
        fmt_note = "✅ AABB chuẩn (5 cột) — sẵn sàng train"
    else:
        label_fmt = "UNKNOWN"
        fmt_note = f"? {avg_cols:.0f} cột trung bình"

    return Response(
        content=json.dumps(
            {
                "image_count": img_count,
                "label_count": label_count,
                "label_format": label_fmt,
                "format_note": fmt_note,
                "sample_lines": sample_lines[:5],
                "target_class": target_class,
                "target_class_id": new_id,
            }
        ),
        media_type="application/json",
    )


@router.post("/datasets/convert")
async def convert_dataset(
    dataset_zip: Annotated[UploadFile, File(description="Source YOLO ZIP to remap.")],
    mapping_json: Annotated[
        str,
        Form(
            description=(
                "JSON object mapping source class name/id to target: "
                '{"Plastic Trash": "TRASH", "bottle": "TRASH"}'
            )
        ),
    ],
) -> Response:
    blob = await dataset_zip.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty zip.")
    try:
        mapping: dict[str, str] = json.loads(mapping_json)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"mapping_json invalid JSON: {exc}") from exc
    if not isinstance(mapping, dict):
        raise HTTPException(status_code=400, detail="mapping_json must be a JSON object.")
    try:
        out_bytes = convert_dataset_zip(blob, mapping)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    filename = (dataset_zip.filename or "dataset").removesuffix(".zip") + "_converted.zip"
    return Response(
        content=out_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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


@router.post("/datasets/merge", response_model=DatasetUploadResponse)
async def merge_datasets(body: MergeDatasetsRequest) -> DatasetUploadResponse:
    """Gộp nhiều dataset đã upload thành 1 dataset mới để train."""
    orchestrator = get_training_orchestrator()
    try:
        payload = orchestrator.merge_datasets(dataset_ids=body.dataset_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DatasetUploadResponse(
        dataset_id=payload["dataset_id"],
        created_at=payload["created_at"],
        summary=payload["summary"],
    )


@router.post("/datasets/merge-zips")
async def merge_zips_endpoint(
    zip_0: Annotated[UploadFile | None, File(description="ZIP dataset cho slot 0")] = None,
    zip_1: Annotated[UploadFile | None, File(description="ZIP dataset cho slot 1")] = None,
    zip_2: Annotated[UploadFile | None, File(description="ZIP dataset cho slot 2")] = None,
    class_0: Annotated[str, Form(description="Target class slot 0: TRASH|WATER|SMOKE")] = "",
    class_1: Annotated[str, Form(description="Target class slot 1: TRASH|WATER|SMOKE")] = "",
    class_2: Annotated[str, Form(description="Target class slot 2: TRASH|WATER|SMOKE")] = "",
) -> Response:
    """Nhận tối đa 3 ZIP (mỗi cái 1 class) → gộp thành 1 ZIP chuẩn YOLO 3-class.

    Form fields: zip_0/zip_1/zip_2 (file), class_0/class_1/class_2 (TRASH|WATER|SMOKE).
    Trả về ZIP download + header X-Stats (JSON).
    """
    slots: list[tuple[bytes, str]] = []
    pairs = [(zip_0, class_0), (zip_1, class_1), (zip_2, class_2)]
    for idx, (upload, cls) in enumerate(pairs):
        if upload is None:
            continue
        blob = await upload.read()
        if not blob:
            continue
        cls = cls.strip().upper()
        if cls not in ("TRASH", "WATER", "SMOKE"):
            raise HTTPException(
                status_code=400,
                detail=f"Slot {idx}: class phải là TRASH, WATER hoặc SMOKE (nhận '{cls}').",
            )
        slots.append((blob, cls))

    if len(slots) < 2:
        raise HTTPException(status_code=400, detail="Cần ít nhất 2 slot ZIP để merge.")

    try:
        merged_bytes, stats = merge_zips_direct(slots)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(
        content=merged_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="merged_dataset.zip"',
            "X-Stats": json.dumps(stats),
        },
    )


@router.post("/jobs", response_model=TrainingJobResponse)
async def create_training_job(body: CreateTrainingJobRequest) -> TrainingJobResponse:
    orchestrator = get_training_orchestrator()
    try:
        payload = orchestrator.create_job(
            dataset_id=body.dataset_id,
            dataset_ids=body.dataset_ids,
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


@router.get("/jobs", response_model=TrainingJobListResponse)
async def list_training_jobs(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> TrainingJobListResponse:
    orchestrator = get_training_orchestrator()
    payload = orchestrator.list_jobs(limit=limit, offset=offset)
    return TrainingJobListResponse(
        items=[TrainingJobResponse(**job) for job in payload["items"]],
        total=payload["total"],
        limit=payload["limit"],
        offset=payload["offset"],
    )


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(job_id: str) -> TrainingJobResponse:
    orchestrator = get_training_orchestrator()
    try:
        payload = orchestrator.get_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TrainingJobResponse(**payload)


@router.post("/jobs/{job_id}/stop", response_model=TrainingJobResponse)
async def stop_training_job(job_id: str) -> TrainingJobResponse:
    orchestrator = get_training_orchestrator()
    try:
        payload = orchestrator.kill_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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


# ---------------------------------------------------------------------------
# Scene Classifier (EfficientNet-B0) training endpoints
# ---------------------------------------------------------------------------


@router.post("/scene/datasets/upload", response_model=SceneDatasetUploadResponse)
async def upload_scene_dataset_zip(
    dataset_zip: Annotated[
        UploadFile,
        File(
            description="Zip with images/train/{WATER,SMOKE,NEGATIVE}/ folders (optionally images/val/)."
        ),
    ],
) -> SceneDatasetUploadResponse:
    blob = await dataset_zip.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty dataset zip.")
    if not dataset_zip.filename:
        raise HTTPException(status_code=400, detail="Dataset filename is required.")
    orchestrator = get_scene_training_orchestrator()
    try:
        payload = orchestrator.upload_dataset(filename=dataset_zip.filename, content=blob)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SceneDatasetUploadResponse(
        dataset_id=payload["dataset_id"],
        created_at=payload["created_at"],
        summary=payload["summary"],
    )


@router.post("/scene/jobs", response_model=SceneTrainingJobResponse)
async def create_scene_training_job(
    body: CreateSceneTrainingJobRequest,
) -> SceneTrainingJobResponse:
    orchestrator = get_scene_training_orchestrator()
    try:
        payload = orchestrator.create_job(
            dataset_id=body.dataset_id,
            run_name=body.run_name,
            epochs=body.epochs,
            batch=body.batch,
            lr=body.lr,
            output_path=body.output_path,
        )
        detail = orchestrator.get_job(payload["job_id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SceneTrainingJobResponse(**detail)


@router.get("/scene/jobs", response_model=SceneTrainingJobListResponse)
async def list_scene_training_jobs(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> SceneTrainingJobListResponse:
    orchestrator = get_scene_training_orchestrator()
    payload = orchestrator.list_jobs(limit=limit, offset=offset)
    return SceneTrainingJobListResponse(
        items=[SceneTrainingJobResponse(**job) for job in payload["items"]],
        total=payload["total"],
        limit=payload["limit"],
        offset=payload["offset"],
    )


@router.get("/scene/jobs/{job_id}", response_model=SceneTrainingJobResponse)
async def get_scene_training_job(job_id: str) -> SceneTrainingJobResponse:
    orchestrator = get_scene_training_orchestrator()
    try:
        payload = orchestrator.get_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SceneTrainingJobResponse(**payload)


@router.get("/scene/jobs/{job_id}/logs", response_model=TrainingLogResponse)
async def get_scene_training_job_logs(
    job_id: str,
    offset: int = 0,
    limit: int = 20000,
) -> TrainingLogResponse:
    orchestrator = get_scene_training_orchestrator()
    try:
        payload = orchestrator.read_log(job_id, offset=offset, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TrainingLogResponse(**payload)
