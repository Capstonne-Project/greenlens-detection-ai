"""Dataset ingestion + local training job orchestration for web dashboard."""

from __future__ import annotations

import csv
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

_VALID_CLASS_IDS = {0, 1, 2, 3}


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

    def list_jobs(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                """
                SELECT * FROM training_jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
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
    if len(bits) != 5:
        return None
    try:
        class_id = int(float(bits[0]))
        x = float(bits[1])
        y = float(bits[2])
        w = float(bits[3])
        h = float(bits[4])
    except ValueError:
        return None
    if class_id not in _VALID_CLASS_IDS:
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
        "names:\n"
        "  0: TRASH\n"
        "  1: WATER\n"
        "  2: SMOKE\n"
        "  3: CHEMICAL\n"
    )
    target_yaml.write_text(payload, encoding="utf-8")


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

    def upload_dataset(self, *, filename: str, content: bytes) -> dict[str, Any]:
        payload = ingest_dataset_zip(filename, content)
        self.store.insert_dataset(payload)
        return payload

    def create_job(
        self,
        *,
        dataset_id: str,
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
        row = self.store.get_dataset(dataset_id)
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
            "dataset_id": dataset_id,
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
                assert proc.stdout is not None
                for line in proc.stdout:
                    logf.write(line)
                    logf.flush()
                code = proc.wait()
        except Exception as exc:  # noqa: BLE001
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

    def list_jobs(self) -> list[dict[str, Any]]:
        rows = self.store.list_jobs()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(_row_to_job_dict(row))
        return out

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
