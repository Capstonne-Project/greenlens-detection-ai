#!/usr/bin/env python3
"""
GreenLens E1 — Fine-tune YOLOv8n on Kaggle (TRASH / WATER, 2 classes).

Setup on Kaggle:
  1. New Notebook → Settings → Accelerator: GPU T4 x2 (or P100)
  2. Add Dataset: upload merged_dataset.zip as Kaggle Dataset (or attach from Output)
  3. Copy this file into a cell OR: !python /kaggle/working/train_greenlens_e1.py

Expected zip layout (from Dashboard merge tool):
  images/train/  images/val/  images/test/
  labels/train/  labels/val/  labels/test/
  data.yaml (optional — script creates one if missing)
"""

from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

# ── Config (edit on Kaggle) ───────────────────────────────────────────────
DATASET_ZIP = os.environ.get(
    "GREENLENS_DATASET_ZIP", "/kaggle/input/greenlens-merged/merged_dataset.zip"
)
EXTRACT_DIR = Path("/kaggle/working/dataset")
EPOCHS = int(os.environ.get("GREENLENS_EPOCHS", "150"))
IMGSZ = int(os.environ.get("GREENLENS_IMGSZ", "1280"))
BATCH = int(os.environ.get("GREENLENS_BATCH", "16"))  # T4 16GB: 16; if OOM use 8
MODEL = os.environ.get("GREENLENS_MODEL", "yolov8n.pt")
RUN_NAME = os.environ.get("GREENLENS_RUN", "greenlens_e1_2class")
SEED = 42


def extract_dataset(zip_path: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    # Flatten single top-level folder if present
    children = [p for p in dest.iterdir() if p.is_dir() and p.name not in ("__MACOSX",)]
    if len(children) == 1 and not (dest / "images").exists():
        inner = children[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(dest / item.name))
        inner.rmdir()


def write_data_yaml(root: Path) -> Path:
    yaml_path = root / "data.yaml"
    if yaml_path.is_file():
        text = yaml_path.read_text(encoding="utf-8")
        if "nc: 2" in text and "TRASH" in text:
            return yaml_path
    content = f"""path: {root.as_posix()}
train: images/train
val: images/val
test: images/test
nc: 2
names:
  0: TRASH
  1: WATER
"""
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path


def count_split(root: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for split in ("train", "val", "test"):
        img_dir = root / "images" / split
        out[split] = len(list(img_dir.glob("*.*"))) if img_dir.is_dir() else 0
    return out


def main() -> None:
    zip_path = Path(DATASET_ZIP)
    if not zip_path.is_file():
        raise SystemExit(
            f"Dataset zip not found: {zip_path}\n"
            "Upload merged_dataset.zip as Kaggle Dataset and set GREENLENS_DATASET_ZIP."
        )

    print("=== [1/4] Extract dataset ===")
    if EXTRACT_DIR.exists():
        shutil.rmtree(EXTRACT_DIR)
    extract_dataset(str(zip_path), EXTRACT_DIR)
    counts = count_split(EXTRACT_DIR)
    print("Images:", counts)
    if counts.get("train", 0) < 10:
        raise SystemExit("Too few train images — check zip structure.")

    data_yaml = write_data_yaml(EXTRACT_DIR)
    print("data.yaml:", data_yaml)

    print("=== [2/4] Install ultralytics ===")
    import subprocess

    subprocess.check_call(["pip", "install", "-q", "ultralytics"])

    print("=== [3/4] Train ===")
    from ultralytics import YOLO

    model = YOLO(MODEL)
    model.train(
        data=str(data_yaml),
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        workers=2,
        project="/kaggle/working/runs",
        name=RUN_NAME,
        seed=SEED,
        patience=30,
        save=True,
        amp=True,
        exist_ok=True,
    )

    run_dir = Path(f"/kaggle/working/runs/{RUN_NAME}")
    best = run_dir / "weights" / "best.pt"
    out_bundle = Path("/kaggle/working/greenlens_e1_output")
    out_bundle.mkdir(exist_ok=True)
    if best.is_file():
        shutil.copy2(best, out_bundle / "best.pt")
    for fname in ("results.csv", "args.yaml"):
        src = run_dir / fname
        if src.is_file():
            shutil.copy2(src, out_bundle / fname)

    print("=== [4/4] Eval on TEST split (paper metric) ===")
    if best.is_file():
        metrics = model.val(data=str(data_yaml), split="test", imgsz=IMGSZ)
        print("TEST metrics:", metrics)

    print("\n" + "=" * 60)
    print("DONE — download from Kaggle Output:")
    print("  /kaggle/working/greenlens_e1_output/best.pt")
    print("  /kaggle/working/greenlens_e1_output/results.csv")
    print("  /kaggle/working/greenlens_e1_output/args.yaml")
    print("=" * 60)


if __name__ == "__main__":
    main()
