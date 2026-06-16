#!/usr/bin/env python3
"""
GreenLens E1 — standalone YOLOv8n train (Kaggle or local).

No GitHub clone needed. Upload this file to Kaggle (Add Data) or paste into notebook:

  !pip install -q ultralytics
  !python train_e1_standalone.py

Default dataset path matches Pollution_merge_VN+NATION on Kaggle.
Override with env GREENLENS_DATA_DIR or --data-dir.

Outputs (under --output-dir, default /kaggle/working/paper_output):
  E1/best.pt
  E1/results.csv
  runs/E1_yolov8n/
  e1_bundle.zip  (Kaggle Output — download this)
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path

DEFAULT_DATA = os.environ.get(
    "GREENLENS_DATA_DIR",
    "/kaggle/input/datasets/hulphc/pollution-merge-vn-nation",
)
DEFAULT_OUT = os.environ.get("GREENLENS_OUTPUT_DIR", "/kaggle/working/paper_output")


def _log(msg: str) -> None:
    print(msg, flush=True)


def _write_data_yaml(data_root: Path, yaml_dir: Path) -> Path:
    yaml_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = yaml_dir / "data.yaml"
    yaml_path.write_text(
        f"""path: {data_root.as_posix()}
train: images/train
val: images/val
test: images/test
nc: 2
names:
  0: TRASH
  1: WATER
""",
        encoding="utf-8",
    )
    return yaml_path


def _count_split(data_root: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for split in ("train", "val", "test"):
        d = data_root / "images" / split
        out[split] = len(list(d.glob("*"))) if d.is_dir() else 0
    return out


def _print_test_metrics(results: object) -> None:
    box = results.box  # type: ignore[attr-defined]
    _log("\n=== E1 TEST (split=test) ===")
    _log(f"ALL  mAP50: {box.map50:.4f}  mAP50-95: {box.map:.4f}")
    _log(f"ALL  P={box.mp:.3f}  R={box.mr:.3f}")
    for i, name in enumerate(("TRASH", "WATER")):
        p, r, ap50, ap = box.class_result(i)
        _log(f"{name:5} mAP50: {ap50:.4f}  P={p:.3f}  R={r:.3f}  mAP50-95: {ap:.4f}")


def _make_bundle_zip(out_dir: Path, bundle_zip: Path) -> None:
    bundle_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in (
            "E1/best.pt",
            "E1/results.csv",
            "data.yaml",
            "runs/E1_yolov8n/weights/best.pt",
            "runs/E1_yolov8n/weights/last.pt",
            "runs/E1_yolov8n/results.csv",
        ):
            src = out_dir / rel
            if src.is_file():
                zf.write(src, rel)
    _log(f"\nBundle: {bundle_zip} ({bundle_zip.stat().st_size / 1e6:.1f} MB)")


def main() -> int:
    parser = argparse.ArgumentParser(description="GreenLens E1 standalone train")
    parser.add_argument("--data-dir", default=DEFAULT_DATA)
    parser.add_argument("--output-dir", default=DEFAULT_OUT)
    parser.add_argument(
        "--epochs", type=int, default=int(os.environ.get("GREENLENS_EPOCHS", "150"))
    )
    parser.add_argument("--imgsz", type=int, default=int(os.environ.get("GREENLENS_IMGSZ", "1280")))
    parser.add_argument("--batch", type=int, default=int(os.environ.get("GREENLENS_BATCH", "8")))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--device", default=os.environ.get("GREENLENS_DEVICE", "0"))
    parser.add_argument("--skip-zip", action="store_true")
    args = parser.parse_args()

    data_root = Path(args.data_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not (data_root / "images" / "train").is_dir():
        _log(f"ERROR: missing {data_root / 'images/train'}")
        _log("Set --data-dir or GREENLENS_DATA_DIR to your YOLO dataset root.")
        return 1

    counts = _count_split(data_root)
    _log(f"Dataset: {data_root}")
    _log(f"Images:  train={counts['train']}  val={counts['val']}  test={counts['test']}")

    data_yaml = _write_data_yaml(data_root, out_dir)
    _log(f"data.yaml -> {data_yaml} (path points to read-only input OK)")

    try:
        from ultralytics import YOLO
    except ImportError:
        _log("ERROR: pip install ultralytics")
        return 1

    run_name = "E1_yolov8n"
    _log("\n=== [1/3] Train YOLOv8n ===")
    model = YOLO("yolov8n.pt")
    model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=2,
        device=args.device,
        project=str(out_dir / "runs"),
        name=run_name,
        seed=args.seed,
        patience=args.patience,
        amp=True,
        exist_ok=True,
    )

    best = out_dir / "runs" / run_name / "weights" / "best.pt"
    if not best.is_file():
        _log(f"ERROR: missing {best}")
        return 1

    bundle = out_dir / "E1"
    bundle.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, bundle / "best.pt")
    results_csv = out_dir / "runs" / run_name / "results.csv"
    if results_csv.is_file():
        shutil.copy2(results_csv, bundle / "results.csv")

    _log("\n=== [2/3] Eval TEST ===")
    model = YOLO(str(best))
    results = model.val(data=str(data_yaml), split="test", imgsz=args.imgsz, verbose=False)
    _print_test_metrics(results)

    _log("\n=== [3/3] Done ===")
    _log(f"best.pt -> {bundle / 'best.pt'}")

    if not args.skip_zip:
        zip_path = out_dir.parent / "e1_bundle.zip"
        if str(out_dir.parent) == "/kaggle/working":
            zip_path = Path("/kaggle/working/e1_bundle.zip")
        _make_bundle_zip(out_dir, zip_path)
        _log("\nKaggle: download e1_bundle.zip from Output panel after Commit completes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
