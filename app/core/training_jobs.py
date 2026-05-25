"""Dataset ingestion + local training job orchestration for web dashboard."""

from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import shutil
import sqlite3
import subprocess
import threading
import time
import traceback
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.utils.logger import get_logger

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_TRAIN_SCRIPT = _PROJECT_ROOT / "ml" / "training" / "train_yolo.py"
_SCENE_TRAIN_SCRIPT = _PROJECT_ROOT / "ml" / "training" / "train_scene_classifier.py"

_UPLOAD_ROOT = _PROJECT_ROOT / "ml" / "training" / "uploads"
_RUNS_ROOT = _PROJECT_ROOT / "ml" / "training" / "runs" / "web_jobs"
_DB_PATH = _PROJECT_ROOT / "ml" / "training" / "runs" / "training_jobs.sqlite3"
_DEFAULT_BASELINE_MODEL = _PROJECT_ROOT / "ml" / "weights" / "yolov8n.pt"

_DATASET_REQUIRED_DIRS = (
    "images/train",
    "images/val",
    "labels/train",
    "labels/val",
)

# Scene classifier dataset: images/train/{WATER,SMOKE,NEGATIVE}/
_SCENE_CLASSES = ("WATER", "SMOKE", "NEGATIVE")
_SCENE_REQUIRED_SUBDIRS = tuple(f"images/train/{cls}" for cls in _SCENE_CLASSES)

_VALID_CLASS_IDS = {0, 1, 2}

# Target class mapping for the project
_TARGET_CLASSES = {"TRASH": 0, "WATER": 1, "SMOKE": 2}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_dirs() -> None:
    _UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    _RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class DatasetValidationSummary:
    image_count: int
    label_count: int
    class_counts: dict[int, int]
    invalid_lines: int


class TrainingJobStore:
    """Tiny sqlite-backed store for training jobs and datasets."""

    def __init__(self) -> None:
        _ensure_dirs()
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS training_datasets (
                  dataset_id TEXT PRIMARY KEY,
                  created_at TEXT NOT NULL,
                  source_zip_path TEXT NOT NULL,
                  extracted_dir TEXT NOT NULL,
                  normalized_dir TEXT NOT NULL,
                  summary_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS training_jobs (
                  job_id TEXT PRIMARY KEY,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  status TEXT NOT NULL,
                  dataset_id TEXT NOT NULL,
                  run_name TEXT NOT NULL,
                  epochs INTEGER NOT NULL,
                  batch INTEGER NOT NULL,
                  imgsz INTEGER NOT NULL,
                  model_path TEXT NOT NULL,
                  project_dir TEXT NOT NULL,
                  output_dir TEXT NOT NULL,
                  stdout_log_path TEXT NOT NULL,
                  result_json TEXT,
                  error_text TEXT
                )
                """
            )
            # Scene classifier datasets and jobs (separate tables for clean API separation)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scene_datasets (
                  dataset_id TEXT PRIMARY KEY,
                  created_at TEXT NOT NULL,
                  source_zip_path TEXT NOT NULL,
                  extracted_dir TEXT NOT NULL,
                  summary_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scene_jobs (
                  job_id TEXT PRIMARY KEY,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  status TEXT NOT NULL,
                  dataset_id TEXT NOT NULL,
                  run_name TEXT NOT NULL,
                  epochs INTEGER NOT NULL,
                  batch INTEGER NOT NULL,
                  lr REAL NOT NULL,
                  data_root TEXT NOT NULL,
                  output_path TEXT NOT NULL,
                  stdout_log_path TEXT NOT NULL,
                  result_json TEXT,
                  error_text TEXT
                )
                """
            )

    def insert_dataset(self, payload: dict[str, Any]) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO training_datasets (
                  dataset_id, created_at, source_zip_path, extracted_dir, normalized_dir, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["dataset_id"],
                    payload["created_at"],
                    payload["source_zip_path"],
                    payload["extracted_dir"],
                    payload["normalized_dir"],
                    json.dumps(payload["summary"], ensure_ascii=True),
                ),
            )

    def get_dataset(self, dataset_id: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM training_datasets WHERE dataset_id = ?",
                (dataset_id,),
            ).fetchone()

    def insert_job(self, payload: dict[str, Any]) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO training_jobs (
                  job_id, created_at, updated_at, status, dataset_id, run_name, epochs,
                  batch, imgsz, model_path, project_dir, output_dir, stdout_log_path, result_json, error_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    payload["job_id"],
                    payload["created_at"],
                    payload["updated_at"],
                    payload["status"],
                    payload["dataset_id"],
                    payload["run_name"],
                    payload["epochs"],
                    payload["batch"],
                    payload["imgsz"],
                    payload["model_path"],
                    payload["project_dir"],
                    payload["output_dir"],
                    payload["stdout_log_path"],
                ),
            )

    def update_job(
        self,
        job_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error_text: str | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE training_jobs
                SET status = ?, updated_at = ?, result_json = ?, error_text = ?
                WHERE job_id = ?
                """,
                (
                    status,
                    _utc_now_iso(),
                    json.dumps(result, ensure_ascii=True) if result is not None else None,
                    error_text,
                    job_id,
                ),
            )

    def count_jobs(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM training_jobs").fetchone()
            return int(row["n"]) if row else 0

    def list_jobs(self, limit: int = 20, offset: int = 0) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                """
                SELECT * FROM training_jobs
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

    def get_job(self, job_id: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM training_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()

    def get_latest_succeeded_job(self) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute(
                """
                SELECT * FROM training_jobs
                WHERE status = 'SUCCEEDED'
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ).fetchone()


def _safe_extract_zip(src: Path, dest: Path) -> None:
    with zipfile.ZipFile(src) as zf:
        for info in zf.infolist():
            resolved = (dest / info.filename).resolve()
            if dest.resolve() not in resolved.parents and resolved != dest.resolve():
                raise ValueError("Unsafe zip path detected.")
        zf.extractall(dest)


def _locate_dataset_root(extracted: Path) -> Path:
    direct_ok = all((extracted / rel).is_dir() for rel in _DATASET_REQUIRED_DIRS)
    if direct_ok:
        return extracted

    nested = [
        child
        for child in extracted.iterdir()
        if child.is_dir() and all((child / rel).is_dir() for rel in _DATASET_REQUIRED_DIRS)
    ]
    if len(nested) == 1:
        return nested[0]
    raise ValueError("Dataset zip must contain images/train,val and labels/train,val.")


def _normalize_label_line(raw: str) -> tuple[int, float, float, float, float] | None:
    bits = raw.strip().split()
    if not bits:
        return None
    try:
        class_id = int(float(bits[0]))
    except ValueError:
        return None
    if class_id not in _VALID_CLASS_IDS:
        return None

    n = len(bits) - 1  # number of coordinate values after class_id

    if n == 4:
        # Standard YOLO: cx cy w h
        try:
            x, y, w, h = float(bits[1]), float(bits[2]), float(bits[3]), float(bits[4])
        except ValueError:
            return None

    elif n == 8:
        # OBB (Oriented Bounding Box): x1 y1 x2 y2 x3 y3 x4 y4 — convert to AABB
        try:
            coords = [float(b) for b in bits[1:9]]
        except ValueError:
            return None
        xs = coords[0::2]
        ys = coords[1::2]
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        x = (x1 + x2) / 2
        y = (y1 + y2) / 2
        w = x2 - x1
        h = y2 - y1

    else:
        return None

    x = min(max(x, 0.0), 1.0)
    y = min(max(y, 0.0), 1.0)
    w = min(max(w, 0.0), 1.0)
    h = min(max(h, 0.0), 1.0)
    return class_id, x, y, w, h


def _normalize_dataset(dataset_root: Path, out_root: Path) -> DatasetValidationSummary:
    image_count = 0
    label_count = 0
    class_counts: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
    invalid_lines = 0

    for rel in _DATASET_REQUIRED_DIRS:
        (out_root / rel).mkdir(parents=True, exist_ok=True)

    for split in ("train", "val"):
        src_image_dir = dataset_root / "images" / split
        src_label_dir = dataset_root / "labels" / split
        dst_image_dir = out_root / "images" / split
        dst_label_dir = out_root / "labels" / split

        for img in src_image_dir.iterdir():
            if img.is_file():
                image_count += 1
                shutil.copy2(img, dst_image_dir / img.name)

        for lab in src_label_dir.glob("*.txt"):
            label_count += 1
            lines = lab.read_text(encoding="utf-8").splitlines()
            normalized_lines: list[str] = []
            for line in lines:
                normalized = _normalize_label_line(line)
                if normalized is None:
                    invalid_lines += 1
                    continue
                cls, x, y, w, h = normalized
                class_counts[cls] += 1
                normalized_lines.append(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
            (dst_label_dir / lab.name).write_text(
                "\n".join(normalized_lines) + ("\n" if normalized_lines else ""),
                encoding="utf-8",
            )

    return DatasetValidationSummary(
        image_count=image_count,
        label_count=label_count,
        class_counts=class_counts,
        invalid_lines=invalid_lines,
    )


def ingest_dataset_zip(filename: str, content: bytes) -> dict[str, Any]:
    dataset_id = f"ds_{uuid.uuid4().hex[:10]}"
    created_at = _utc_now_iso()

    zip_path = _UPLOAD_ROOT / f"{dataset_id}_{Path(filename).name}"
    zip_path.write_bytes(content)

    extracted_dir = _UPLOAD_ROOT / f"{dataset_id}_raw"
    normalized_dir = _UPLOAD_ROOT / f"{dataset_id}_normalized"
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir, ignore_errors=True)
    if normalized_dir.exists():
        shutil.rmtree(normalized_dir, ignore_errors=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    _safe_extract_zip(zip_path, extracted_dir)
    dataset_root = _locate_dataset_root(extracted_dir)
    summary = _normalize_dataset(dataset_root, normalized_dir)

    return {
        "dataset_id": dataset_id,
        "created_at": created_at,
        "source_zip_path": str(zip_path.resolve()),
        "extracted_dir": str(extracted_dir.resolve()),
        "normalized_dir": str(normalized_dir.resolve()),
        "summary": {
            "image_count": summary.image_count,
            "label_count": summary.label_count,
            "class_counts": summary.class_counts,
            "invalid_lines": summary.invalid_lines,
            "required_structure": list(_DATASET_REQUIRED_DIRS),
        },
    }


def _prepare_training_data_yaml(dataset_dir: Path, target_yaml: Path) -> None:
    payload = (
        f"path: {dataset_dir.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "nc: 3\n"
        "names:\n"
        "  0: TRASH\n"
        "  1: WATER\n"
        "  2: SMOKE\n"
    )
    target_yaml.write_text(payload, encoding="utf-8")


def merge_normalized_datasets(source_dirs: list[Path], merged_dir: Path) -> dict[str, Any]:
    """Copy images + labels từ nhiều normalized dataset vào 1 thư mục merged.

    Mỗi file được prefix bằng dataset index để tránh trùng tên.
    Trả về summary: số ảnh/label mỗi split và class distribution.
    """
    merged_dir.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val"):
        (merged_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (merged_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {
        "train_images": 0,
        "val_images": 0,
        "train_labels": 0,
        "val_labels": 0,
    }
    class_counts: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}

    for ds_idx, src in enumerate(source_dirs):
        prefix = f"ds{ds_idx:02d}_"
        for split in ("train", "val"):
            img_src = src / "images" / split
            lbl_src = src / "labels" / split
            img_dst = merged_dir / "images" / split
            lbl_dst = merged_dir / "labels" / split

            if not img_src.exists():
                continue

            for img_file in img_src.iterdir():
                if not img_file.is_file():
                    continue
                dst_name = prefix + img_file.name
                shutil.copy2(img_file, img_dst / dst_name)
                counts[f"{split}_images"] += 1

                # Copy label với cùng stem
                lbl_file = lbl_src / (img_file.stem + ".txt")
                if lbl_file.exists():
                    dst_lbl = lbl_dst / (prefix + img_file.stem + ".txt")
                    shutil.copy2(lbl_file, dst_lbl)
                    counts[f"{split}_labels"] += 1
                    # Count classes
                    for line in lbl_file.read_text(encoding="utf-8").splitlines():
                        parts = line.strip().split()
                        if parts:
                            try:
                                cls_id = int(parts[0])
                                if cls_id in class_counts:
                                    class_counts[cls_id] += 1
                            except ValueError:
                                pass

    return {
        "train_images": counts["train_images"],
        "val_images": counts["val_images"],
        "train_labels": counts["train_labels"],
        "val_labels": counts["val_labels"],
        "class_counts": {str(k): v for k, v in class_counts.items()},
        "source_count": len(source_dirs),
    }


def _parse_results_csv(results_path: Path) -> dict[str, Any] | None:
    if not results_path.is_file():
        return None
    with results_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {"latest": None, "rows": 0}
    latest = rows[-1]
    return {
        "rows": len(rows),
        "latest": latest,
        "columns": list(latest.keys()),
    }


class TrainingOrchestrator:
    """Runs local training jobs in background threads, stores state in sqlite."""

    def __init__(self) -> None:
        self.store = TrainingJobStore()
        self._logger = get_logger(__name__)
        self._procs: dict[str, subprocess.Popen[str]] = {}  # job_id -> live process
        self._procs_lock = threading.Lock()

    def upload_dataset(self, *, filename: str, content: bytes) -> dict[str, Any]:
        payload = ingest_dataset_zip(filename, content)
        self.store.insert_dataset(payload)
        return payload

    def merge_datasets(self, *, dataset_ids: list[str]) -> dict[str, Any]:
        """Gộp nhiều dataset thành 1 dataset mới, lưu vào DB và trả về dataset_id."""
        if len(dataset_ids) < 2:
            raise ValueError("Cần ít nhất 2 dataset_id để merge.")

        rows = []
        for ds_id in dataset_ids:
            row = self.store.get_dataset(ds_id)
            if row is None:
                raise ValueError(f"Unknown dataset_id: {ds_id}")
            rows.append(row)

        merged_id = f"ds_{uuid.uuid4().hex[:10]}"
        now = _utc_now_iso()
        merged_dir = _UPLOAD_ROOT / f"{merged_id}_normalized"

        source_dirs = [Path(row["normalized_dir"]) for row in rows]
        summary = merge_normalized_datasets(source_dirs, merged_dir)
        summary["source_dataset_ids"] = dataset_ids

        payload = {
            "dataset_id": merged_id,
            "created_at": now,
            "source_zip_path": f"merged:{'+'.join(dataset_ids)}",
            "extracted_dir": str(merged_dir),
            "normalized_dir": str(merged_dir),
            "summary": summary,
        }
        self.store.insert_dataset(payload)
        return payload

    def create_job(
        self,
        *,
        dataset_id: str,
        dataset_ids: list[str] | None = None,
        run_name: str,
        epochs: int,
        batch: int,
        imgsz: int,
        model_path: str | None,
        continue_from_latest: bool,
        continue_from_job_id: str | None,
        enable_wandb: bool,
        wandb_project: str | None,
        wandb_entity: str | None,
        wandb_api_key: str | None,
    ) -> dict[str, Any]:
        # Nếu truyền nhiều dataset_ids thì merge trước
        effective_ids = dataset_ids if dataset_ids and len(dataset_ids) > 1 else [dataset_id]
        if len(effective_ids) > 1:
            merged = self.merge_datasets(dataset_ids=effective_ids)
            resolved_dataset_id = merged["dataset_id"]
            row = self.store.get_dataset(resolved_dataset_id)
        else:
            resolved_dataset_id = effective_ids[0]
            row = self.store.get_dataset(resolved_dataset_id)

        if row is None:
            raise ValueError("Unknown dataset_id.")

        job_id = f"job_{uuid.uuid4().hex[:10]}"
        now = _utc_now_iso()
        job_dir = _RUNS_ROOT / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        output_dir = job_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        train_yaml = job_dir / "train_data.yaml"
        _prepare_training_data_yaml(Path(row["normalized_dir"]), train_yaml)
        resolved_model_path = self._resolve_model_path(
            model_path=model_path,
            continue_from_latest=continue_from_latest,
            continue_from_job_id=continue_from_job_id,
        )

        log_path = job_dir / "train.log"
        payload = {
            "job_id": job_id,
            "created_at": now,
            "updated_at": now,
            "status": "QUEUED",
            "dataset_id": resolved_dataset_id,
            "run_name": run_name,
            "epochs": epochs,
            "batch": batch,
            "imgsz": imgsz,
            "model_path": resolved_model_path,
            "project_dir": str(output_dir.resolve()),
            "output_dir": str((output_dir / run_name).resolve()),
            "stdout_log_path": str(log_path.resolve()),
        }
        self.store.insert_job(payload)
        thread = threading.Thread(
            target=self._run_job,
            args=(
                job_id,
                str(train_yaml.resolve()),
                epochs,
                batch,
                imgsz,
                resolved_model_path,
                str(output_dir.resolve()),
                run_name,
                enable_wandb,
                wandb_project,
                wandb_entity,
                wandb_api_key,
            ),
            daemon=True,
        )
        thread.start()
        return payload

    def _resolve_model_path(
        self,
        *,
        model_path: str | None,
        continue_from_latest: bool,
        continue_from_job_id: str | None,
    ) -> str:
        if continue_from_job_id:
            source_job = self.store.get_job(continue_from_job_id)
            if source_job is None:
                raise ValueError("continue_from_job_id not found.")
            if source_job["status"] != "SUCCEEDED":
                raise ValueError("continue_from_job_id must reference a SUCCEEDED job.")
            source_payload = _row_to_job_dict(source_job)
            source_result = source_payload.get("result")
            if not isinstance(source_result, dict):
                raise ValueError("Source job does not contain result payload.")
            best_model_path = source_result.get("best_model_path")
            if not isinstance(best_model_path, str):
                raise ValueError("Source job is missing best_model_path.")
            best_model = Path(best_model_path).resolve()
            if not best_model.is_file():
                raise ValueError("Source job best_model_path does not exist on disk.")
            return str(best_model)

        if model_path and model_path.strip():
            explicit_model = Path(model_path).resolve()
            if not explicit_model.is_file():
                raise ValueError(f"model_path does not exist: {explicit_model}")
            return str(explicit_model)

        if continue_from_latest:
            latest_job = self.store.get_latest_succeeded_job()
            if latest_job is not None:
                latest_payload = _row_to_job_dict(latest_job)
                latest_result = latest_payload.get("result")
                if isinstance(latest_result, dict):
                    latest_best_model = latest_result.get("best_model_path")
                    if isinstance(latest_best_model, str):
                        latest_best_path = Path(latest_best_model).resolve()
                        if latest_best_path.is_file():
                            return str(latest_best_path)

        if _DEFAULT_BASELINE_MODEL.is_file():
            return str(_DEFAULT_BASELINE_MODEL.resolve())
        return "yolov8n.pt"

    def _run_job(
        self,
        job_id: str,
        data_yaml_path: str,
        epochs: int,
        batch: int,
        imgsz: int,
        model_path: str,
        project_dir: str,
        run_name: str,
        enable_wandb: bool,
        wandb_project: str | None,
        wandb_entity: str | None,
        wandb_api_key: str | None,
    ) -> None:
        row = self.store.get_job(job_id)
        if row is None:
            return
        log_path = Path(row["stdout_log_path"])
        self.store.update_job(job_id, status="RUNNING")
        env = dict(**os.environ)
        if enable_wandb:
            env["WANDB_MODE"] = "online"
            if wandb_project:
                env["WANDB_PROJECT"] = wandb_project
            if wandb_entity:
                env["WANDB_ENTITY"] = wandb_entity
            if wandb_api_key:
                env["WANDB_API_KEY"] = wandb_api_key
        else:
            env["WANDB_MODE"] = "disabled"

        cmd = [
            "uv",
            "run",
            "python",
            str(_TRAIN_SCRIPT.resolve()),
            "--data",
            data_yaml_path,
            "--model",
            model_path,
            "--epochs",
            str(epochs),
            "--batch",
            str(batch),
            "--workers",
            "0",
            "--imgsz",
            str(imgsz),
            "--project",
            project_dir,
            "--name",
            run_name,
        ]
        self._logger.info("training_job_start", job_id=job_id, command=" ".join(cmd))
        start_ts = time.time()
        try:
            with log_path.open("w", encoding="utf-8") as logf:
                proc = subprocess.Popen(  # noqa: S603
                    cmd,
                    cwd=str(_PROJECT_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=env,
                )
                with self._procs_lock:
                    self._procs[job_id] = proc
                assert proc.stdout is not None
                for line in proc.stdout:
                    logf.write(line)
                    logf.flush()
                code = proc.wait()
                with self._procs_lock:
                    self._procs.pop(job_id, None)
        except Exception as exc:  # noqa: BLE001
            with self._procs_lock:
                self._procs.pop(job_id, None)
            with log_path.open("a", encoding="utf-8") as logf:
                logf.write("\n[orchestrator_error] Web training crashed while streaming logs.\n")
                logf.write(f"{type(exc).__name__}: {exc}\n")
                logf.write(traceback.format_exc())
            self.store.update_job(
                job_id,
                status="FAILED",
                result={
                    "exit_code": None,
                    "duration_seconds": round(time.time() - start_ts, 2),
                    "best_model_path": str(
                        (Path(row["output_dir"]) / "weights" / "best.pt").resolve()
                    ),
                    "last_model_path": str(
                        (Path(row["output_dir"]) / "weights" / "last.pt").resolve()
                    ),
                    "results_csv": str((Path(row["output_dir"]) / "results.csv").resolve()),
                    "results_png": str((Path(row["output_dir"]) / "results.png").resolve()),
                    "wandb_enabled": enable_wandb,
                    "wandb_project": wandb_project,
                    "wandb_entity": wandb_entity,
                },
                error_text=f"Training orchestrator crashed: {type(exc).__name__}: {exc}",
            )
            self._logger.exception("training_job_crashed", job_id=job_id)
            return

        output_dir = Path(row["output_dir"])
        result_payload = {
            "exit_code": code,
            "duration_seconds": round(time.time() - start_ts, 2),
            "best_model_path": str((output_dir / "weights" / "best.pt").resolve()),
            "last_model_path": str((output_dir / "weights" / "last.pt").resolve()),
            "results_csv": str((output_dir / "results.csv").resolve()),
            "results_png": str((output_dir / "results.png").resolve()),
            "wandb_enabled": enable_wandb,
            "wandb_project": wandb_project,
            "wandb_entity": wandb_entity,
        }
        if code == 0:
            self.store.update_job(job_id, status="SUCCEEDED", result=result_payload)
            self._logger.info("training_job_success", job_id=job_id)
        else:
            self.store.update_job(
                job_id,
                status="FAILED",
                result=result_payload,
                error_text=f"Training failed with exit code {code}",
            )
            self._logger.warning("training_job_failed", job_id=job_id, exit_code=code)

    def kill_job(self, job_id: str) -> dict[str, Any]:
        """Terminate a running training job process."""
        row = self.store.get_job(job_id)
        if row is None:
            raise ValueError("Unknown job_id.")
        if row["status"] not in ("RUNNING", "QUEUED"):
            raise ValueError(f"Job is not running (status={row['status']}).")
        with self._procs_lock:
            proc = self._procs.get(job_id)
        if proc is not None:
            with contextlib.suppress(Exception):
                proc.kill()
            with self._procs_lock:
                self._procs.pop(job_id, None)
        self.store.update_job(job_id, status="FAILED", error_text="Cancelled by user.")
        return self.get_job(job_id)

    def _enrich_job_payload(
        self, payload: dict[str, Any], dataset_cache: dict[str, Any]
    ) -> dict[str, Any]:
        ds_id = payload.get("dataset_id")
        if ds_id and ds_id not in dataset_cache:
            ds_row = self.store.get_dataset(ds_id)
            if ds_row and ds_row["summary_json"]:
                dataset_cache[ds_id] = json.loads(ds_row["summary_json"])
            else:
                dataset_cache[ds_id] = None
        if ds_id:
            payload["dataset_summary"] = dataset_cache.get(ds_id)

        result = payload.get("result")
        if isinstance(result, dict):
            csv_path = result.get("results_csv")
            if isinstance(csv_path, str):
                parsed = _parse_results_csv(Path(csv_path))
                if parsed is not None:
                    payload["metrics"] = parsed
        return payload

    def list_jobs(self, *, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        rows = self.store.list_jobs(limit=limit, offset=offset)
        total = self.store.count_jobs()
        dataset_cache: dict[str, Any] = {}
        items: list[dict[str, Any]] = []
        for row in rows:
            payload = _row_to_job_dict(row)
            self._enrich_job_payload(payload, dataset_cache)
            items.append(payload)
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_job(self, job_id: str) -> dict[str, Any]:
        row = self.store.get_job(job_id)
        if row is None:
            raise ValueError("Unknown job_id.")
        payload = _row_to_job_dict(row)
        log_path = Path(row["stdout_log_path"])
        if log_path.is_file():
            payload["log_size_bytes"] = log_path.stat().st_size
        result = payload.get("result")
        if isinstance(result, dict):
            csv_path = result.get("results_csv")
            if isinstance(csv_path, str):
                parsed = _parse_results_csv(Path(csv_path))
                if parsed is not None:
                    payload["metrics"] = parsed
        # Attach dataset summary so the dashboard can show image/class counts
        ds_row = self.store.get_dataset(row["dataset_id"])
        if ds_row and ds_row["summary_json"]:
            payload["dataset_summary"] = json.loads(ds_row["summary_json"])
        return payload

    def read_log(self, job_id: str, *, offset: int = 0, limit: int = 20000) -> dict[str, Any]:
        row = self.store.get_job(job_id)
        if row is None:
            raise ValueError("Unknown job_id.")
        log_path = Path(row["stdout_log_path"])
        if not log_path.is_file():
            return {"content": "", "next_offset": 0, "eof": True}
        blob = log_path.read_text(encoding="utf-8", errors="replace")
        start = max(offset, 0)
        end = min(start + max(limit, 1), len(blob))
        chunk = blob[start:end]
        return {
            "content": chunk,
            "next_offset": end,
            "eof": end >= len(blob),
            "total_size": len(blob),
            "status": row["status"],
        }


# ---------------------------------------------------------------------------
# Dataset inspect + convert (class remap)
# ---------------------------------------------------------------------------


def _parse_yaml_names(text: str) -> dict[int, str]:
    """Parse 'names:' block from a YOLO data.yaml — no external yaml dep needed."""
    names: dict[int, str] = {}
    in_names = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        # Handle list form:  names: [cls0, cls1, ...]
        if line.lstrip().startswith("names:") and "[" in line:
            inside = line[line.index("[") + 1 : line.rindex("]")]
            for i, part in enumerate(inside.split(",")):
                names[i] = part.strip().strip("'\"")
            break
        # Handle dict/list block form
        if line.lstrip().startswith("names:"):
            in_names = True
            continue
        if in_names:
            if not line.startswith(" ") and not line.startswith("\t") and line.strip():
                break
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # dict form:  0: ClassName
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                with contextlib.suppress(ValueError):
                    names[int(key.strip())] = val.strip().strip("'\"")
            # list form:  - ClassName
            elif stripped.startswith("- "):
                names[len(names)] = stripped[2:].strip().strip("'\"")
    return names


def inspect_dataset_zip(content: bytes) -> dict[str, Any]:
    """Open a ZIP in-memory, find YAML config, return detected class names."""
    detected_classes: dict[int, str] = {}
    yaml_filename: str | None = None

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names_in_zip = zf.namelist()
        # Find first .yaml file (data config)
        yaml_candidates = [n for n in names_in_zip if n.lower().endswith((".yaml", ".yml"))]
        if yaml_candidates:
            yaml_filename = yaml_candidates[0]
            yaml_text = zf.read(yaml_filename).decode("utf-8", errors="replace")
            detected_classes = _parse_yaml_names(yaml_text)

        # Fallback: count unique class IDs from label txt files
        if not detected_classes:
            found_ids: set[int] = set()
            for name in names_in_zip:
                if name.lower().endswith(".txt") and (
                    "label" in name.lower() or "train" in name.lower()
                ):
                    try:
                        txt = zf.read(name).decode("utf-8", errors="replace")
                        for line in txt.splitlines():
                            parts = line.strip().split()
                            if parts:
                                with contextlib.suppress(ValueError):
                                    found_ids.add(int(float(parts[0])))
                    except Exception:  # noqa: BLE001
                        pass
            for cid in sorted(found_ids):
                detected_classes[cid] = str(cid)

    return {
        "yaml_file": yaml_filename,
        "detected_classes": detected_classes,  # {0: "Plastic Trash", 1: "bottle", ...}
        "target_classes": {v: k for k, v in _TARGET_CLASSES.items()},  # {0: "TRASH", ...}
    }


def convert_dataset_zip(content: bytes, mapping: dict[str, str]) -> bytes:
    """Remap class IDs in all label .txt files inside the ZIP.

    mapping: source class name (or str int) -> target class name (TRASH/WATER/SMOKE)
    Classes mapped to None / not in mapping are DROPPED (lines removed).
    Returns new ZIP bytes with remapped labels and updated data.yaml.
    """
    # Build old_id -> new_id lookup.
    # mapping keys can be class names OR string int IDs.
    # We first need to know the original id->name from the ZIP's yaml.
    info = inspect_dataset_zip(content)
    orig_id_to_name: dict[int, str] = info["detected_classes"]
    # name -> original id (case-insensitive)
    name_to_orig_id = {v.lower(): k for k, v in orig_id_to_name.items()}

    # Normalise mapping keys: resolve both "Plastic Trash" and "0" forms
    old_id_to_new_id: dict[int, int] = {}
    for src_key, tgt_class in mapping.items():
        tgt_class_upper = tgt_class.strip().upper()
        if tgt_class_upper not in _TARGET_CLASSES:
            continue  # skip / drop
        new_id = _TARGET_CLASSES[tgt_class_upper]
        # Try as int id first
        try:
            old_id = int(src_key)
            old_id_to_new_id[old_id] = new_id
            continue
        except ValueError:
            pass
        # Try as class name
        resolved = name_to_orig_id.get(src_key.lower())
        if resolved is not None:
            old_id_to_new_id[resolved] = new_id

    out_buf = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(content)) as src_zf,
        zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as dst_zf,
    ):
        for item in src_zf.infolist():
            data = src_zf.read(item.filename)
            name_lower = item.filename.lower()

            if name_lower.endswith(".txt") and not name_lower.endswith("requirements.txt"):
                # Remap label lines
                lines_in = data.decode("utf-8", errors="replace").splitlines()
                lines_out: list[str] = []
                for line in lines_in:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    try:
                        old_id = int(float(parts[0]))
                    except ValueError:
                        continue
                    new_id = old_id_to_new_id.get(old_id)
                    if new_id is None:
                        continue  # drop unmapped class
                    lines_out.append(f"{new_id} " + " ".join(parts[1:]))
                dst_zf.writestr(item, "\n".join(lines_out) + ("\n" if lines_out else ""))

            elif name_lower.endswith((".yaml", ".yml")):
                # Rewrite yaml names block
                try:
                    yaml_text = data.decode("utf-8", errors="replace")
                    new_yaml = _rewrite_yaml_names(yaml_text)
                    dst_zf.writestr(item, new_yaml.encode("utf-8"))
                except Exception:  # noqa: BLE001
                    dst_zf.writestr(item, data)

            else:
                dst_zf.writestr(item, data)

    return out_buf.getvalue()


def _rewrite_yaml_names(yaml_text: str) -> str:
    """Replace the names block in a YOLO yaml with the 3 target classes."""
    new_names_block = "names:\n" "  0: TRASH\n" "  1: WATER\n" "  2: SMOKE\n"
    lines = yaml_text.splitlines(keepends=True)
    out: list[str] = []
    skip = False
    names_written = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("names:"):
            out.append(new_names_block)
            names_written = True
            skip = True
            continue
        if skip:
            # Stop skipping when we hit a non-indented non-empty line
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                skip = False
                out.append(line)
            continue
        out.append(line)
    if not names_written:
        out.append(new_names_block)
    return "".join(out)


def restructure_dataset_zip(content: bytes, val_fraction: float = 0.15) -> bytes:
    """Convert a flat train+labels ZIP to images/train,val + labels/train,val YOLO layout.

    Accepted input layouts (auto-detected):
      A)  train/<img>  +  labels/<img_stem>.txt
      B)  train/<img>  +  train/<img_stem>.txt   (labels mixed with images)
      C)  images/<img> +  labels/<img_stem>.txt
      D)  <img> at root + labels/<img_stem>.txt

    Output always:
      images/train/  images/val/  labels/train/  labels/val/
    Labels are normalised (OBB→AABB, coords clamped).
    val_fraction of images are randomly assigned to val (seed stable per zip).
    """
    import random as _rnd

    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        all_names = zf.namelist()

        # ---- collect all image paths and their bytes ----
        img_entries: dict[str, bytes] = {}  # stem -> (zip_path, bytes)
        img_path_map: dict[str, str] = {}  # stem -> original zip path
        for name in all_names:
            p = Path(name)
            if p.suffix.lower() in image_exts and not name.startswith("__MACOSX"):
                stem = p.stem
                img_entries[stem] = zf.read(name)
                img_path_map[stem] = name

        # ---- collect label files: stem -> raw txt bytes ----
        label_entries: dict[str, bytes] = {}
        for name in all_names:
            p = Path(name)
            if p.suffix.lower() == ".txt" and not name.startswith("__MACOSX"):
                # skip yaml-style files
                if p.name in ("requirements.txt",):
                    continue
                stem = p.stem
                label_entries[stem] = zf.read(name)

    if not img_entries:
        raise ValueError("No image files found in ZIP (jpg/png/bmp/webp/tiff).")

    # ---- train/val split ----
    stems = sorted(img_entries.keys())
    _rnd.seed(42)
    _rnd.shuffle(stems)
    n_val = max(1, int(len(stems) * val_fraction))
    val_stems = set(stems[:n_val])

    # ---- build output ZIP ----
    out_buf = io.BytesIO()
    stats = {"train_images": 0, "val_images": 0, "train_labels": 0, "val_labels": 0, "no_label": 0}

    with zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for stem in stems:
            split = "val" if stem in val_stems else "train"
            orig_path = img_path_map[stem]
            ext = Path(orig_path).suffix.lower()
            img_bytes = img_entries[stem]

            dst.writestr(f"images/{split}/{stem}{ext}", img_bytes)
            stats[f"{split}_images"] += 1

            raw_label = label_entries.get(stem)
            if raw_label is None:
                stats["no_label"] += 1
                # write empty label file so YOLO doesn't complain
                dst.writestr(f"labels/{split}/{stem}.txt", b"")
                continue

            # normalise label lines (handles OBB + standard YOLO)
            lines_in = raw_label.decode("utf-8", errors="replace").splitlines()
            lines_out: list[str] = []
            for line in lines_in:
                parsed = _normalize_label_line(line)
                if parsed is None:
                    continue
                cls, x, y, w, h = parsed
                lines_out.append(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")

            dst.writestr(
                f"labels/{split}/{stem}.txt",
                ("\n".join(lines_out) + ("\n" if lines_out else "")).encode(),
            )
            stats[f"{split}_labels"] += 1

        # Write a minimal data.yaml so our inspect endpoint works on it later
        yaml_content = (
            "path: .\n"
            "train: images/train\n"
            "val: images/val\n"
            "nc: 3\n"
            "names:\n"
            "  0: TRASH\n"
            "  1: WATER\n"
            "  2: SMOKE\n"
        )
        dst.writestr("data.yaml", yaml_content.encode())

    return out_buf.getvalue(), stats


def split_dataset_zip(content: bytes, split_count: int) -> tuple[bytes, bytes, dict]:
    """Split a YOLO-structured ZIP into two ZIPs, keeping image/label pairs matched.

    Accepts any YOLO layout (flat or images/*/labels/* or mixed).
    Returns (split_zip_bytes, remainder_zip_bytes, stats_dict).
    split_count: number of image-label pairs to put in the first (split) ZIP.
    """
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        all_names = zf.namelist()

        # Collect all entries as raw bytes keyed by zip path
        all_data: dict[str, bytes] = {n: zf.read(n) for n in all_names}

        # Identify image files: stem -> zip_path
        img_path_map: dict[str, str] = {}
        for name in all_names:
            p = Path(name)
            if p.suffix.lower() in image_exts and not name.startswith("__MACOSX"):
                stem = p.stem
                img_path_map[stem] = name

        # Identify label files: stem -> zip_path
        label_path_map: dict[str, str] = {}
        for name in all_names:
            p = Path(name)
            if (
                p.suffix.lower() == ".txt"
                and not name.startswith("__MACOSX")
                and p.name not in ("requirements.txt",)
            ):
                stem = p.stem
                label_path_map[stem] = name

    if not img_path_map:
        raise ValueError("No image files found in ZIP (jpg/png/bmp/webp/tiff).")

    total = len(img_path_map)
    if split_count < 1 or split_count >= total:
        raise ValueError(
            f"split_count must be between 1 and {total - 1} (dataset has {total} images)."
        )

    # Deterministic order for reproducibility
    stems_sorted = sorted(img_path_map.keys())
    split_stems = set(stems_sorted[:split_count])
    remainder_stems = set(stems_sorted[split_count:])

    # Non-image, non-label files (yaml, notes, etc.) go into both ZIPs
    matched_paths: set[str] = set(img_path_map.values()) | set(label_path_map.values())
    shared_paths = [n for n in all_names if n not in matched_paths and not n.startswith("__MACOSX")]

    def _build_zip(stems: set[str]) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as dst:
            # shared files (yaml, etc.)
            for path in shared_paths:
                dst.writestr(path, all_data[path])
            # matched pairs
            for stem in sorted(stems):
                img_path = img_path_map[stem]
                dst.writestr(img_path, all_data[img_path])
                label_path = label_path_map.get(stem)
                if label_path:
                    dst.writestr(label_path, all_data[label_path])
        return buf.getvalue()

    split_zip = _build_zip(split_stems)
    remainder_zip = _build_zip(remainder_stems)

    stats = {
        "total_images": total,
        "split_images": len(split_stems),
        "remainder_images": len(remainder_stems),
        "split_paired_labels": sum(1 for s in split_stems if s in label_path_map),
        "remainder_paired_labels": sum(1 for s in remainder_stems if s in label_path_map),
    }
    return split_zip, remainder_zip, stats


def filter_classes_zip(content: bytes, keep_ids: set[int]) -> tuple[bytes, dict]:
    """Remove images + labels whose annotations contain ONLY unwanted class IDs.

    Logic per image stem:
      - Parse its label file (if any).
      - Keep lines whose class ID is in keep_ids; drop the rest.
      - If NO kept lines remain AND the image had at least one annotation → drop
        the image + label pair entirely from the ZIP.
      - Images with NO label file at all are kept (background/negative samples).
      - All non-image, non-label files (yaml, notes...) are preserved as-is,
        but the yaml names block is rewritten to only list kept classes
        with re-indexed IDs starting from 0.

    Returns (filtered_zip_bytes, stats_dict).
    stats keys: total_images, kept_images, dropped_images,
                total_label_files, kept_label_files, dropped_label_files,
                total_annotations, kept_annotations, dropped_annotations.
    """
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        all_names = zf.namelist()
        all_data: dict[str, bytes] = {}
        for n in all_names:
            if not n.endswith("/"):
                all_data[n] = zf.read(n)

    # stem -> zip path for images
    img_path_map: dict[str, str] = {}
    for name in all_names:
        p = Path(name)
        if p.suffix.lower() in image_exts and not name.startswith("__MACOSX"):
            img_path_map[p.stem] = name

    # stem -> zip path for labels
    label_path_map: dict[str, str] = {}
    for name in all_names:
        p = Path(name)
        if (
            p.suffix.lower() == ".txt"
            and not name.startswith("__MACOSX")
            and p.name not in ("requirements.txt",)
        ):
            label_path_map[p.stem] = name

    if not img_path_map:
        raise ValueError("No image files found in ZIP (jpg/png/bmp/webp/tiff).")

    # Build old_id -> new_id remapping so kept classes are re-indexed 0,1,2,...
    old_to_new: dict[int, int] = {old: new for new, old in enumerate(sorted(keep_ids))}

    stats = {
        "total_images": len(img_path_map),
        "kept_images": 0,
        "dropped_images": 0,
        "total_label_files": 0,
        "kept_label_files": 0,
        "dropped_label_files": 0,
        "total_annotations": 0,
        "kept_annotations": 0,
        "dropped_annotations": 0,
    }

    # Decide which stems to keep and build filtered label content
    kept_stems: dict[str, bytes | None] = {}  # stem -> new label bytes (None = no label)

    for stem in sorted(img_path_map):
        label_path = label_path_map.get(stem)

        if label_path is None:
            # No label → keep image (negative/background sample)
            kept_stems[stem] = None
            continue

        raw = all_data[label_path].decode("utf-8", errors="replace")
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        stats["total_label_files"] += 1
        stats["total_annotations"] += len(lines)

        kept_lines: list[str] = []
        dropped_count = 0
        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue
            try:
                cid = int(float(parts[0]))
            except ValueError:
                continue
            if cid in keep_ids:
                new_cid = old_to_new[cid]
                kept_lines.append(f"{new_cid} " + " ".join(parts[1:]))
            else:
                dropped_count += 1

        stats["kept_annotations"] += len(kept_lines)
        stats["dropped_annotations"] += dropped_count

        if not kept_lines and lines:
            # All annotations were unwanted → drop entire image+label pair
            stats["dropped_images"] += 1
            stats["dropped_label_files"] += 1
            continue

        stats["kept_label_files"] += 1
        kept_stems[stem] = ("\n".join(kept_lines) + "\n").encode()

    stats["kept_images"] = len(kept_stems)

    # Paths that are neither images nor labels (yaml, notes, etc.)
    all_img_paths = set(img_path_map.values())
    all_label_paths = set(label_path_map.values())
    shared_paths = [
        n
        for n in all_names
        if n not in all_img_paths
        and n not in all_label_paths
        and not n.startswith("__MACOSX")
        and not n.endswith("/")
    ]

    out_buf = io.BytesIO()
    with zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        # Shared files — rewrite yaml to reflect new class list
        for path in shared_paths:
            data = all_data[path]
            if path.lower().endswith((".yaml", ".yml")):
                try:
                    yaml_text = data.decode("utf-8", errors="replace")
                    data = _rewrite_yaml_names_filtered(yaml_text, keep_ids, old_to_new).encode()
                except Exception:  # noqa: BLE001
                    pass
            dst.writestr(path, data)

        # Kept image+label pairs
        for stem, label_bytes in kept_stems.items():
            img_path = img_path_map[stem]
            dst.writestr(img_path, all_data[img_path])
            if label_bytes is not None:
                dst.writestr(label_path_map[stem], label_bytes)

    return out_buf.getvalue(), stats


def _rewrite_yaml_names_filtered(
    yaml_text: str,
    keep_ids: set[int],
    old_to_new: dict[int, int],
) -> str:
    """Rewrite the names block in a YOLO yaml keeping only the specified class IDs,
    re-indexed to 0,1,2,..."""
    # Parse existing names from the yaml
    existing = _parse_yaml_names(yaml_text)
    # Build new names block with only kept classes, re-indexed
    new_names_lines = ["names:"]
    for old_id in sorted(keep_ids):
        new_id = old_to_new[old_id]
        name = existing.get(old_id, str(old_id))
        new_names_lines.append(f"  {new_id}: {name}")
    new_names_block = "\n".join(new_names_lines) + "\n"

    # Also update nc: line
    nc_value = len(keep_ids)

    lines = yaml_text.splitlines(keepends=True)
    out: list[str] = []
    skip = False
    names_written = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("nc:"):
            out.append(f"nc: {nc_value}\n")
            continue
        if stripped.startswith("names:"):
            out.append(new_names_block)
            names_written = True
            skip = True
            continue
        if skip:
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                skip = False
                out.append(line)
            continue
        out.append(line)
    if not names_written:
        out.append(new_names_block)
    return "".join(out)


def _row_to_job_dict(row: sqlite3.Row) -> dict[str, Any]:
    result: dict[str, Any] | None = None
    if row["result_json"]:
        result = json.loads(row["result_json"])
    return {
        "job_id": row["job_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "status": row["status"],
        "dataset_id": row["dataset_id"],
        "run_name": row["run_name"],
        "epochs": row["epochs"],
        "batch": row["batch"],
        "imgsz": row["imgsz"],
        "model_path": row["model_path"],
        "project_dir": row["project_dir"],
        "output_dir": row["output_dir"],
        "stdout_log_path": row["stdout_log_path"],
        "result": result,
        "error_text": row["error_text"],
    }


_ORCHESTRATOR: TrainingOrchestrator | None = None


def get_training_orchestrator() -> TrainingOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = TrainingOrchestrator()
    return _ORCHESTRATOR


# ---------------------------------------------------------------------------
# Scene classifier dataset ingestion helpers
# ---------------------------------------------------------------------------


def _locate_scene_dataset_root(extracted: Path) -> Path:
    """Find the directory that contains images/train/{WATER,SMOKE,NEGATIVE}."""
    # Direct match
    if all((extracted / rel).is_dir() for rel in _SCENE_REQUIRED_SUBDIRS):
        return extracted
    # One level nested
    nested = [
        child
        for child in extracted.iterdir()
        if child.is_dir() and all((child / rel).is_dir() for rel in _SCENE_REQUIRED_SUBDIRS)
    ]
    if len(nested) == 1:
        return nested[0]
    # Accept partial: at least one class folder present under images/train/
    partial = [
        child
        for child in extracted.iterdir()
        if child.is_dir()
        and (child / "images" / "train").is_dir()
        and any((child / "images" / "train" / cls).is_dir() for cls in _SCENE_CLASSES)
    ]
    if len(partial) == 1:
        return partial[0]
    direct_train = extracted / "images" / "train"
    if direct_train.is_dir() and any((direct_train / cls).is_dir() for cls in _SCENE_CLASSES):
        return extracted
    raise ValueError(
        "Scene dataset zip must contain images/train/{WATER,SMOKE,NEGATIVE}/ folder structure. "
        "At least one class folder is required."
    )


def _ingest_scene_dataset_zip(filename: str, content: bytes) -> dict[str, Any]:
    dataset_id = f"sds_{uuid.uuid4().hex[:10]}"
    created_at = _utc_now_iso()

    _UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    zip_path = _UPLOAD_ROOT / f"{dataset_id}_{Path(filename).name}"
    zip_path.write_bytes(content)

    extracted_dir = _UPLOAD_ROOT / f"{dataset_id}_raw"
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir, ignore_errors=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    _safe_extract_zip(zip_path, extracted_dir)
    dataset_root = _locate_scene_dataset_root(extracted_dir)

    # Count images per class
    class_counts: dict[str, int] = {}
    total_images = 0
    for cls in _SCENE_CLASSES:
        cls_dir = dataset_root / "images" / "train" / cls
        if cls_dir.is_dir():
            imgs = [f for f in cls_dir.iterdir() if f.is_file()]
            class_counts[cls] = len(imgs)
            total_images += len(imgs)
        else:
            class_counts[cls] = 0

    # Also count optional val split
    val_counts: dict[str, int] = {}
    for cls in _SCENE_CLASSES:
        val_dir = dataset_root / "images" / "val" / cls
        if val_dir.is_dir():
            val_counts[cls] = len([f for f in val_dir.iterdir() if f.is_file()])

    return {
        "dataset_id": dataset_id,
        "created_at": created_at,
        "source_zip_path": str(zip_path.resolve()),
        "extracted_dir": str(dataset_root.resolve()),
        "summary": {
            "total_train_images": total_images,
            "train_class_counts": class_counts,
            "val_class_counts": val_counts,
            "classes": list(_SCENE_CLASSES),
            "dataset_root": str(dataset_root.resolve()),
        },
    }


# ---------------------------------------------------------------------------
# Scene classifier store methods (added as standalone functions using the
# shared TrainingJobStore which already has the tables after _init_db)
# ---------------------------------------------------------------------------


def _store_insert_scene_dataset(store: TrainingJobStore, payload: dict[str, Any]) -> None:
    with store._lock, store._conn() as conn:
        conn.execute(
            """
            INSERT INTO scene_datasets (dataset_id, created_at, source_zip_path, extracted_dir, summary_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload["dataset_id"],
                payload["created_at"],
                payload["source_zip_path"],
                payload["extracted_dir"],
                json.dumps(payload["summary"], ensure_ascii=True),
            ),
        )


def _store_get_scene_dataset(store: TrainingJobStore, dataset_id: str) -> sqlite3.Row | None:
    with store._conn() as conn:
        return conn.execute(
            "SELECT * FROM scene_datasets WHERE dataset_id = ?", (dataset_id,)
        ).fetchone()


def _store_insert_scene_job(store: TrainingJobStore, payload: dict[str, Any]) -> None:
    with store._lock, store._conn() as conn:
        conn.execute(
            """
            INSERT INTO scene_jobs (
              job_id, created_at, updated_at, status, dataset_id, run_name,
              epochs, batch, lr, data_root, output_path, stdout_log_path, result_json, error_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            """,
            (
                payload["job_id"],
                payload["created_at"],
                payload["updated_at"],
                payload["status"],
                payload["dataset_id"],
                payload["run_name"],
                payload["epochs"],
                payload["batch"],
                payload["lr"],
                payload["data_root"],
                payload["output_path"],
                payload["stdout_log_path"],
            ),
        )


def _store_update_scene_job(
    store: TrainingJobStore,
    job_id: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    error_text: str | None = None,
) -> None:
    with store._lock, store._conn() as conn:
        conn.execute(
            """
            UPDATE scene_jobs
            SET status = ?, updated_at = ?, result_json = ?, error_text = ?
            WHERE job_id = ?
            """,
            (
                status,
                _utc_now_iso(),
                json.dumps(result, ensure_ascii=True) if result is not None else None,
                error_text,
                job_id,
            ),
        )


def _store_get_scene_job(store: TrainingJobStore, job_id: str) -> sqlite3.Row | None:
    with store._conn() as conn:
        return conn.execute("SELECT * FROM scene_jobs WHERE job_id = ?", (job_id,)).fetchone()


def _store_count_scene_jobs(store: TrainingJobStore) -> int:
    with store._conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM scene_jobs").fetchone()
        return int(row["n"]) if row else 0


def _store_list_scene_jobs(
    store: TrainingJobStore, limit: int = 20, offset: int = 0
) -> list[sqlite3.Row]:
    with store._conn() as conn:
        return conn.execute(
            "SELECT * FROM scene_jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()


def _scene_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    result: dict[str, Any] | None = None
    if row["result_json"]:
        result = json.loads(row["result_json"])
    return {
        "job_id": row["job_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "status": row["status"],
        "dataset_id": row["dataset_id"],
        "run_name": row["run_name"],
        "epochs": row["epochs"],
        "batch": row["batch"],
        "lr": row["lr"],
        "data_root": row["data_root"],
        "output_path": row["output_path"],
        "stdout_log_path": row["stdout_log_path"],
        "result": result,
        "error_text": row["error_text"],
    }


# ---------------------------------------------------------------------------
# Scene classifier orchestrator
# ---------------------------------------------------------------------------


class SceneTrainingOrchestrator:
    """Runs scene classifier fine-tuning jobs in background threads."""

    def __init__(self) -> None:
        self.store = TrainingJobStore()
        self._logger = get_logger(__name__)

    def upload_dataset(self, *, filename: str, content: bytes) -> dict[str, Any]:
        payload = _ingest_scene_dataset_zip(filename, content)
        _store_insert_scene_dataset(self.store, payload)
        return payload

    def create_job(
        self,
        *,
        dataset_id: str,
        run_name: str,
        epochs: int,
        batch: int,
        lr: float,
        output_path: str | None,
    ) -> dict[str, Any]:
        row = _store_get_scene_dataset(self.store, dataset_id)
        if row is None:
            raise ValueError("Unknown scene dataset_id.")

        job_id = f"scj_{uuid.uuid4().hex[:10]}"
        now = _utc_now_iso()
        job_dir = _RUNS_ROOT / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        data_root = row["extracted_dir"]
        resolved_output = output_path or str(
            (_PROJECT_ROOT / "ml" / "weights" / "scene_classifier.pt").resolve()
        )
        log_path = job_dir / "train.log"

        payload: dict[str, Any] = {
            "job_id": job_id,
            "created_at": now,
            "updated_at": now,
            "status": "QUEUED",
            "dataset_id": dataset_id,
            "run_name": run_name,
            "epochs": epochs,
            "batch": batch,
            "lr": lr,
            "data_root": data_root,
            "output_path": resolved_output,
            "stdout_log_path": str(log_path.resolve()),
        }
        _store_insert_scene_job(self.store, payload)

        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, data_root, epochs, batch, lr, resolved_output),
            daemon=True,
        )
        thread.start()
        return payload

    def _run_job(
        self,
        job_id: str,
        data_root: str,
        epochs: int,
        batch: int,
        lr: float,
        output_path: str,
    ) -> None:
        row = _store_get_scene_job(self.store, job_id)
        if row is None:
            return
        log_path = Path(row["stdout_log_path"])
        _store_update_scene_job(self.store, job_id, status="RUNNING")
        env = dict(**os.environ)
        env["WANDB_MODE"] = "disabled"
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [
            "uv",
            "run",
            "python",
            str(_SCENE_TRAIN_SCRIPT.resolve()),
            "--data-root",
            data_root,
            "--epochs",
            str(epochs),
            "--batch-size",
            str(batch),
            "--lr",
            str(lr),
            "--workers",
            "0",
            "--output",
            output_path,
        ]
        self._logger.info("scene_job_start", job_id=job_id, command=" ".join(cmd))
        start_ts = time.time()
        try:
            with log_path.open("w", encoding="utf-8") as logf:
                proc = subprocess.Popen(  # noqa: S603
                    cmd,
                    cwd=str(_PROJECT_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=env,
                )
                assert proc.stdout is not None
                for line in proc.stdout:
                    logf.write(line)
                    logf.flush()
                code = proc.wait()
        except Exception as exc:  # noqa: BLE001
            with log_path.open("a", encoding="utf-8") as logf:
                logf.write("\n[orchestrator_error] Scene training crashed.\n")
                logf.write(traceback.format_exc())
            _store_update_scene_job(
                self.store,
                job_id,
                status="FAILED",
                error_text=f"{type(exc).__name__}: {exc}",
            )
            return

        duration = round(time.time() - start_ts, 2)
        result_payload: dict[str, Any] = {
            "exit_code": code,
            "duration_seconds": duration,
            "output_path": output_path,
        }
        if code == 0:
            _store_update_scene_job(self.store, job_id, status="SUCCEEDED", result=result_payload)
            self._logger.info("scene_job_success", job_id=job_id, duration=duration)
        else:
            _store_update_scene_job(
                self.store,
                job_id,
                status="FAILED",
                result=result_payload,
                error_text=f"Training failed with exit code {code}",
            )
            self._logger.warning("scene_job_failed", job_id=job_id, exit_code=code)

    def list_jobs(self, *, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        rows = _store_list_scene_jobs(self.store, limit=limit, offset=offset)
        total = _store_count_scene_jobs(self.store)
        dataset_cache: dict[str, Any] = {}
        items: list[dict[str, Any]] = []
        for row in rows:
            payload = _scene_row_to_dict(row)
            ds_id = payload.get("dataset_id")
            if ds_id and ds_id not in dataset_cache:
                ds_row = _store_get_scene_dataset(self.store, ds_id)
                if ds_row and ds_row["summary_json"]:
                    dataset_cache[ds_id] = json.loads(ds_row["summary_json"])
                else:
                    dataset_cache[ds_id] = None
            if ds_id:
                payload["dataset_summary"] = dataset_cache.get(ds_id)
            items.append(payload)
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_job(self, job_id: str) -> dict[str, Any]:
        row = _store_get_scene_job(self.store, job_id)
        if row is None:
            raise ValueError("Unknown scene job_id.")
        payload = _scene_row_to_dict(row)
        log_path = Path(row["stdout_log_path"])
        if log_path.is_file():
            payload["log_size_bytes"] = log_path.stat().st_size
        ds_row = _store_get_scene_dataset(self.store, row["dataset_id"])
        if ds_row and ds_row["summary_json"]:
            payload["dataset_summary"] = json.loads(ds_row["summary_json"])
        return payload

    def read_log(self, job_id: str, *, offset: int = 0, limit: int = 20000) -> dict[str, Any]:
        row = _store_get_scene_job(self.store, job_id)
        if row is None:
            raise ValueError("Unknown scene job_id.")
        log_path = Path(row["stdout_log_path"])
        if not log_path.is_file():
            return {"content": "", "next_offset": 0, "eof": True}
        blob = log_path.read_text(encoding="utf-8", errors="replace")
        start = max(offset, 0)
        end = min(start + max(limit, 1), len(blob))
        chunk = blob[start:end]
        return {
            "content": chunk,
            "next_offset": end,
            "eof": end >= len(blob),
            "total_size": len(blob),
            "status": row["status"],
        }


_SCENE_ORCHESTRATOR: SceneTrainingOrchestrator | None = None


def get_scene_training_orchestrator() -> SceneTrainingOrchestrator:
    global _SCENE_ORCHESTRATOR
    if _SCENE_ORCHESTRATOR is None:
        _SCENE_ORCHESTRATOR = SceneTrainingOrchestrator()
    return _SCENE_ORCHESTRATOR


# ---------------------------------------------------------------------------
# Merge ZIPs directly (in-memory, no DB) — dùng cho tool "Gộp 3 class"
# ---------------------------------------------------------------------------


def _obb_line_to_aabb(parts: list[str]) -> list[str] | None:
    """Convert 1 dòng OBB (class x1 y1 x2 y2 x3 y3 x4 y4) → AABB (class xc yc w h).

    OBB dùng 4 góc tuyệt đối (9 giá trị) hoặc relative (9 giá trị).
    AABB = bounding box bao quanh nhỏ nhất, tọa độ normalize 0-1.
    Trả None nếu không parse được.
    """
    if len(parts) < 9:
        return None
    try:
        cls_id = parts[0]
        coords = [float(v) for v in parts[1:9]]
        xs = coords[0::2]  # x1, x2, x3, x4
        ys = coords[1::2]  # y1, y2, y3, y4
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        xc = (x_min + x_max) / 2
        yc = (y_min + y_max) / 2
        w = x_max - x_min
        h = y_max - y_min
        # Clamp to [0, 1]
        xc = max(0.0, min(1.0, xc))
        yc = max(0.0, min(1.0, yc))
        w = max(0.0, min(1.0, w))
        h = max(0.0, min(1.0, h))
        if w < 1e-6 or h < 1e-6:
            return None
        return [cls_id, f"{xc:.6f}", f"{yc:.6f}", f"{w:.6f}", f"{h:.6f}"]
    except (ValueError, IndexError):
        return None


def merge_zips_direct(
    slots: list[tuple[bytes, str]],
) -> tuple[bytes, dict[str, Any]]:
    """Nhận tối đa 3 cặp (zip_bytes, target_class) và gộp thành 1 ZIP duy nhất.

    target_class phải là "TRASH" | "WATER" | "SMOKE".
    Mỗi slot được force-remap toàn bộ class_id về đúng target.
    Trả về (merged_zip_bytes, stats).

    stats keys:
      slots: list of {target_class, images, labels, sample_labels}
      total_images, total_labels
      class_counts: {"0": n_trash, "1": n_water, "2": n_smoke}
      data_yaml: str (nội dung data.yaml được nhúng vào ZIP)
    """
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}
    valid_targets = {"TRASH": 0, "WATER": 1, "SMOKE": 2}

    # ── output buffers ──────────────────────────────────────────────────────
    # Gộp vào cấu trúc YOLO chuẩn: images/train/, images/val/, labels/train/, labels/val/
    # Ảnh và label được prefix ds{i}_ để tránh trùng tên.
    out_entries: dict[str, bytes] = {}  # zip_path -> bytes
    stats_slots: list[dict[str, Any]] = []
    class_counts: dict[int, int] = {0: 0, 1: 0, 2: 0}
    total_images = 0
    total_labels = 0

    for slot_idx, (zip_bytes, target_class) in enumerate(slots):
        target_class = target_class.strip().upper()
        if target_class not in valid_targets:
            raise ValueError(
                f"Slot {slot_idx}: target_class phải là TRASH/WATER/SMOKE, nhận '{target_class}'"
            )
        new_class_id = valid_targets[target_class]
        prefix = f"ds{slot_idx:02d}_"

        slot_images = 0
        slot_labels = 0
        sample_labels: list[str] = []  # preview vài dòng đầu

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            all_names = zf.namelist()

            # ── locate images & labels inside zip ──────────────────────────
            # Hỗ trợ cả flat (tên file trực tiếp) lẫn chuẩn (images/train/...)
            img_map: dict[str, tuple[str, str]] = {}  # stem -> (zip_path, split)
            lbl_map: dict[str, tuple[str, str]] = {}  # stem -> (zip_path, split)

            for name in all_names:
                if name.startswith("__MACOSX") or name.endswith("/"):
                    continue
                p = Path(name)
                # Determine split from path segments
                parts_lower = [seg.lower() for seg in p.parts]
                split = "val" if "val" in parts_lower else "train"

                if p.suffix.lower() in image_exts:
                    img_map[p.stem] = (name, split)
                elif p.suffix.lower() == ".txt" and p.name not in (
                    "requirements.txt",
                    "README.txt",
                ):
                    lbl_map[p.stem] = (name, split)

            # ── copy images ────────────────────────────────────────────────
            for stem, (zip_path, split) in img_map.items():
                ext = Path(zip_path).suffix
                dst_path = f"images/{split}/{prefix}{stem}{ext}"
                out_entries[dst_path] = zf.read(zip_path)
                slot_images += 1

            # ── remap & copy labels (auto OBB→AABB) ───────────────────────
            for stem, (zip_path, split) in lbl_map.items():
                raw_txt = zf.read(zip_path).decode("utf-8", errors="replace")
                remapped_lines: list[str] = []
                for line in raw_txt.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    # Auto-convert OBB (9 cols) → AABB (5 cols)
                    if len(parts) >= 9:
                        converted = _obb_line_to_aabb(parts)
                        if converted is None:
                            continue
                        parts = converted
                    elif len(parts) > 5:
                        parts = parts[:5]  # trim extra columns
                    # Force-replace class_id → target
                    parts[0] = str(new_class_id)
                    remapped_lines.append(" ".join(parts))
                    class_counts[new_class_id] += 1

                if not remapped_lines:
                    continue

                dst_path = f"labels/{split}/{prefix}{stem}.txt"
                out_entries[dst_path] = ("\n".join(remapped_lines) + "\n").encode()
                slot_labels += 1

                # Lấy sample label để preview UI (tối đa 3 dòng đầu của slot)
                if len(sample_labels) < 3:
                    sample_labels.extend(remapped_lines[:2])

        total_images += slot_images
        total_labels += slot_labels
        stats_slots.append(
            {
                "target_class": target_class,
                "class_id": new_class_id,
                "images": slot_images,
                "labels": slot_labels,
                "sample_labels": sample_labels[:3],
            }
        )

    if total_images == 0:
        raise ValueError("Không tìm thấy ảnh nào trong các ZIP đã upload.")

    # ── Tạo data.yaml chuẩn 3 class ────────────────────────────────────────
    data_yaml = (
        "path: .\n"
        "train: images/train\n"
        "val: images/val\n"
        "nc: 3\n"
        "names:\n"
        "  0: TRASH\n"
        "  1: WATER\n"
        "  2: SMOKE\n"
    )
    out_entries["data.yaml"] = data_yaml.encode()

    # ── Pack into output ZIP ────────────────────────────────────────────────
    out_buf = io.BytesIO()
    with zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for path, data in out_entries.items():
            dst.writestr(path, data)

    stats = {
        "slots": stats_slots,
        "total_images": total_images,
        "total_labels": total_labels,
        "class_counts": {str(k): v for k, v in class_counts.items()},
        "data_yaml": data_yaml,
    }
    return out_buf.getvalue(), stats
