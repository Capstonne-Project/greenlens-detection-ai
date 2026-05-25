#!/usr/bin/env python3
"""
Fine-tune YOLO pollution detector (Ultralytics).

Prerequisites:
  - Dataset under paths in configs/pollution_data.yaml (see comments in YAML).
  - Optional baseline weights next to PROJECT_ROOT/ml/weights/yolov8n.pt (from scripts/download_baseline_weights.py).

Output:
  - runs/detect/<name>/weights/best.pt  — copy to ml/weights/ and set MODEL_PATH in .env

Usage (from repo root):
  uv run python ml/training/train_yolo.py --epochs 30
  uv run python ml/training/train_yolo.py --data ml/training/configs/pollution_data.yaml --model ml/weights/yolov8n.pt
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train pollution YOLO (TRASH/WATER/SMOKE) — 3 classes, joint training."
    )
    parser.add_argument(
        "--data",
        default=str(_PROJECT_ROOT / "ml" / "training" / "configs" / "pollution_data.yaml"),
        help="Path to Ultralytics dataset YAML.",
    )
    parser.add_argument(
        "--model",
        default=str(_PROJECT_ROOT / "ml" / "weights" / "yolov8n.pt"),
        help="Initial weights (.pt). Use downloaded yolov8n.pt or your previous best.pt.",
    )
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="DataLoader worker processes (set 0 for safer web/background runs on Windows).",
    )
    parser.add_argument("--project", default="ml/training/runs")
    parser.add_argument("--name", default="pollution_detect")
    args = parser.parse_args()

    data_path = Path(args.data).resolve()
    model_path = Path(args.model).resolve()
    if not data_path.is_file():
        raise SystemExit(f"Missing dataset YAML: {data_path}")

    ckpt = str(model_path if model_path.is_file() else "yolov8n.pt")

    print("Project root:", _PROJECT_ROOT)
    print("data:", data_path)
    print("model:", ckpt)
    print("epochs:", args.epochs, "| imgsz:", args.imgsz, "| batch:", args.batch)
    print("workers:", args.workers)

    runs_project = (_PROJECT_ROOT / args.project).resolve()
    runs_project.mkdir(parents=True, exist_ok=True)

    model = YOLO(ckpt)
    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        project=str(runs_project),
        name=args.name,
        exist_ok=True,
    )

    out = runs_project / args.name / "weights" / "best.pt"
    out_abs = out.resolve()
    weights_dest = (_PROJECT_ROOT / "ml" / "weights" / "best.pt").resolve()

    print("\n" + "=" * 60)
    print("[DONE] Training finished!")
    print("=" * 60)
    print(f"  best.pt  : {out_abs}")
    print(f"  exists   : {out_abs.is_file()}")
    print()
    print("--- Paste vao .env ---------------------------------")
    print("  MODEL_PATH=ml/weights/best.pt")
    print(f"  MODEL_VERSION=v?.?.0-<ten_dataset>-{args.epochs}ep")
    print()
    print("--- Copy lenh (chay tu repo root) ------------------")
    print(f'  copy "{out_abs}" "{weights_dest}"')
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
