#!/usr/bin/env python3
"""
GreenLens — chạy thí nghiệm paper (E0, E1, E1b) trên Kaggle hoặc local.

Usage (Kaggle, sau khi attach dataset):
  !pip install -q ultralytics
  !python ml/training/kaggle/run_paper_experiments.py --mode all --dataset-zip /kaggle/input/.../merged_dataset.zip

Modes:
  e0       — eval YOLOv8n COCO pretrained on TEST (no train)
  e1       — train YOLOv8n + eval TEST
  e1b      — train YOLOv8s + eval TEST (optional larger baseline)
  eval     — eval existing best.pt on TEST
  all      — e0 + e1 (default paper minimum)

Output:
  /kaggle/working/paper_output/paper_metrics.json
  /kaggle/working/paper_output/BANG_IV.md  ← dán vào PAPER_FULL_PLAYBOOK_VI.md
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Shared train config (must match paper §5.1)
DEFAULT_EPOCHS = 150
DEFAULT_IMGSZ = 1280
DEFAULT_BATCH = 8
DEFAULT_SEED = 42
CLASS_NAMES = ("TRASH", "WATER")


def _extract_dataset(zip_path: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    children = [p for p in dest.iterdir() if p.is_dir() and p.name != "__MACOSX"]
    if len(children) == 1 and not (dest / "images").exists():
        inner = children[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(dest / item.name))
        inner.rmdir()


def _write_data_yaml(root: Path, *, yaml_dir: Path | None = None) -> Path:
    """Write Ultralytics data.yaml. Use yaml_dir when root is read-only (e.g. /kaggle/input)."""
    dest_dir = yaml_dir if yaml_dir is not None else root
    dest_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = dest_dir / "data.yaml"
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


def _metrics_from_val(results: Any) -> dict[str, Any]:
    """Extract detection metrics from Ultralytics val return value."""
    box = results.box
    out: dict[str, Any] = {
        "all": {
            "precision": round(float(box.mp), 4),
            "recall": round(float(box.mr), 4),
            "map50": round(float(box.map50), 4),
            "map50_95": round(float(box.map), 4),
        },
        "per_class": {},
    }
    maps50 = list(box.maps50) if hasattr(box, "maps50") and box.maps50 is not None else []
    if not maps50 and hasattr(box, "ap50") and callable(box.ap50):
        maps50 = list(box.ap50())
    # Fallback: per-class mAP@0.5:0.95 list (older API)
    if not maps50 and hasattr(box, "maps") and box.maps is not None:
        maps50 = list(box.maps)

    for i, name in enumerate(CLASS_NAMES):
        cls: dict[str, Any] = {
            "map50": round(float(maps50[i]), 4) if i < len(maps50) else None,
            "map50_95": None,
            "precision": None,
            "recall": None,
        }
        if hasattr(box, "p") and box.p is not None and len(box.p) > i:
            cls["precision"] = round(float(box.p[i]), 4)
        if hasattr(box, "r") and box.r is not None and len(box.r) > i:
            cls["recall"] = round(float(box.r[i]), 4)
        if hasattr(box, "maps") and box.maps is not None and len(box.maps) > i:
            cls["map50_95"] = round(float(box.maps[i]), 4)
        out["per_class"][name] = cls
    return out


def _run_val(model_path: str, data_yaml: Path, imgsz: int) -> dict[str, Any]:
    from ultralytics import YOLO

    model = YOLO(model_path)
    results = model.val(data=str(data_yaml), split="test", imgsz=imgsz, verbose=False)
    return _metrics_from_val(results)


def _run_train(
    *,
    model_init: str,
    data_yaml: Path,
    run_name: str,
    project: Path,
    epochs: int,
    imgsz: int,
    batch: int,
    seed: int,
) -> Path:
    from ultralytics import YOLO

    project.mkdir(parents=True, exist_ok=True)
    model = YOLO(model_init)
    model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        workers=2,
        project=str(project),
        name=run_name,
        seed=seed,
        patience=30,
        save=True,
        amp=True,
        exist_ok=True,
    )
    best = project / run_name / "weights" / "best.pt"
    if not best.is_file():
        raise FileNotFoundError(f"Missing best.pt at {best}")
    return best


def _experiment_record(
    exp_id: str,
    label: str,
    fine_tuned: bool,
    model_init: str,
    metrics: dict[str, Any],
    weights: str | None = None,
) -> dict[str, Any]:
    all_m = metrics["all"]
    trash = metrics["per_class"].get("TRASH", {})
    water = metrics["per_class"].get("WATER", {})
    return {
        "id": exp_id,
        "label": label,
        "fine_tuned": fine_tuned,
        "model_init": model_init,
        "weights": weights,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "metrics": metrics,
        "table_row": {
            "method": label,
            "fine_tune": "Có" if fine_tuned else "Không",
            "trash_p": trash.get("precision"),
            "trash_r": trash.get("recall"),
            "trash_map50": trash.get("map50"),
            "trash_map50_95": trash.get("map50_95"),
            "water_p": water.get("precision"),
            "water_r": water.get("recall"),
            "water_map50": water.get("map50"),
            "water_map50_95": water.get("map50_95"),
            "all_map50": all_m.get("map50"),
        },
    }


def _render_bang_iv(experiments: list[dict[str, Any]]) -> str:
    role_map = {
        "E0": "Baseline",
        "E1": "Baseline FT *(detector trong GreenLens)*",
        "E1B": "Baseline (opt)",
    }
    lines = [
        "### Bảng IV — KẾT QUẢ THỰC TẾ (auto-generated)",
        "",
        "> **GreenLens (Ours)** = E3 full pipeline. Script Kaggle chỉ auto chạy **E0 + E1**; thêm E2/E3 thủ công sau.",
        "",
        "| Vai trò | Method | Fine-tune | TRASH mAP50 | WATER mAP50 | ALL mAP50 | TRASH P | WATER P |",
        "|---------|--------|-----------|-------------|-------------|-----------|---------|---------|",
    ]
    for exp in experiments:
        r = exp["table_row"]
        role = role_map.get(exp["id"], "—")
        lines.append(
            f"| {role} | {r['method']} | {r['fine_tune']} | "
            f"{r['trash_map50']} | {r['water_map50']} | {r['all_map50']} | "
            f"{r['trash_p']} | {r['water_p']} |"
        )
    lines.extend(
        [
            "",
            "| **Ours** | E2 GreenLens-Det | Có | = E1 | Bảng V | = E1 | — | — |",
            "| **Ours ★** | **E3 GreenLens-Full** | Có | = E1 | Bảng V | = E1 | — | — |",
            "",
            "★ **E3 = model đề xuất chính** (YOLO + scene + subtype + API).",
        ]
    )
    if len(experiments) >= 2:
        e0 = next((e for e in experiments if e["id"] == "E0"), None)
        e1 = next((e for e in experiments if e["id"] == "E1"), None)
        if e0 and e1:
            m0 = e0["table_row"]["all_map50"] or 0
            m1 = e1["table_row"]["all_map50"] or 0
            if m0 > 0:
                delta = (m1 - m0) / m0 * 100
                lines.extend(["", f"**ΔmAP E1 vs E0:** +{delta:.1f}%", ""])
    lines.append(f"\n_Generated: {datetime.now(UTC).isoformat()}_")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="GreenLens paper experiments E0/E1/E1b")
    parser.add_argument(
        "--mode",
        choices=("e0", "e1", "e1b", "eval", "all"),
        default="all",
        help="e0=baseline COCO, e1=train v8n, e1b=train v8s, all=e0+e1",
    )
    parser.add_argument(
        "--dataset-zip",
        default=os.environ.get(
            "GREENLENS_DATASET_ZIP",
            "/kaggle/input/greenlens-merged-2class/merged_dataset.zip",
        ),
    )
    parser.add_argument("--dataset-dir", default="", help="Skip zip if folder already extracted")
    parser.add_argument("--weights", default="", help="For --mode eval only")
    parser.add_argument("--output-dir", default="/kaggle/working/paper_output")
    parser.add_argument(
        "--epochs", type=int, default=int(os.environ.get("GREENLENS_EPOCHS", DEFAULT_EPOCHS))
    )
    parser.add_argument(
        "--imgsz", type=int, default=int(os.environ.get("GREENLENS_IMGSZ", DEFAULT_IMGSZ))
    )
    parser.add_argument(
        "--batch", type=int, default=int(os.environ.get("GREENLENS_BATCH", DEFAULT_BATCH))
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    work = (
        Path("/kaggle/working/dataset") if Path("/kaggle/working").exists() else out_dir / "dataset"
    )

    if args.dataset_dir:
        data_root = Path(args.dataset_dir)
    else:
        zip_path = Path(args.dataset_zip)
        if not zip_path.is_file():
            raise SystemExit(f"Dataset zip not found: {zip_path}")
        _extract_dataset(zip_path, work)
        data_root = work

    yaml_dir = out_dir if not os.access(data_root, os.W_OK) else None
    if yaml_dir is not None:
        print(f"Dataset read-only ({data_root}) — writing data.yaml to {yaml_dir}")
    data_yaml = _write_data_yaml(data_root, yaml_dir=yaml_dir)
    runs_project = out_dir / "runs"
    experiments: list[dict[str, Any]] = []

    # Load previous results if re-running partial
    metrics_file = out_dir / "paper_metrics.json"
    if metrics_file.is_file():
        prev = json.loads(metrics_file.read_text(encoding="utf-8"))
        experiments = [e for e in prev.get("experiments", []) if e["id"] not in {"E0", "E1", "E1B"}]

    def save() -> None:
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "data_yaml": str(data_yaml),
            "train_config": {
                "epochs": args.epochs,
                "imgsz": args.imgsz,
                "batch": args.batch,
                "seed": args.seed,
            },
            "experiments": experiments,
        }
        metrics_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        bang = _render_bang_iv(experiments)
        (out_dir / "BANG_IV.md").write_text(bang, encoding="utf-8")
        print(bang)

    if args.mode in ("e0", "all"):
        print("\n=== E0: YOLOv8n COCO — eval TEST only ===")
        m0 = _run_val("yolov8n.pt", data_yaml, args.imgsz)
        experiments = [e for e in experiments if e["id"] != "E0"]
        experiments.append(_experiment_record("E0", "E0 YOLOv8n-COCO", False, "yolov8n.pt", m0))
        save()

    if args.mode in ("e1", "all"):
        print("\n=== E1: Train YOLOv8n + eval TEST ===")
        best = _run_train(
            model_init="yolov8n.pt",
            data_yaml=data_yaml,
            run_name="E1_yolov8n",
            project=runs_project,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            seed=args.seed,
        )
        bundle = out_dir / "E1"
        bundle.mkdir(exist_ok=True)
        shutil.copy2(best, bundle / "best.pt")
        run_dir = best.parent.parent
        for f in ("results.csv", "args.yaml"):
            src = run_dir / f
            if src.is_file():
                shutil.copy2(src, bundle / f)
        m1 = _run_val(str(best), data_yaml, args.imgsz)
        experiments = [e for e in experiments if e["id"] != "E1"]
        experiments.append(
            _experiment_record(
                "E1", "E1 FT-YOLOv8n (GreenLens detector)", True, "yolov8n.pt", m1, str(best)
            )
        )
        save()

    if args.mode == "e1b":
        print("\n=== E1b: Train YOLOv8s + eval TEST (optional) ===")
        best = _run_train(
            model_init="yolov8s.pt",
            data_yaml=data_yaml,
            run_name="E1b_yolov8s",
            project=runs_project,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            seed=args.seed,
        )
        bundle = out_dir / "E1b"
        bundle.mkdir(exist_ok=True)
        shutil.copy2(best, bundle / "best.pt")
        m1b = _run_val(str(best), data_yaml, args.imgsz)
        experiments = [e for e in experiments if e["id"] != "E1B"]
        experiments.append(
            _experiment_record("E1B", "E1b FT-YOLOv8s", True, "yolov8s.pt", m1b, str(best))
        )
        save()

    if args.mode == "eval":
        if not args.weights:
            raise SystemExit("--weights required for --mode eval")
        print(f"\n=== Eval only: {args.weights} ===")
        m = _run_val(args.weights, data_yaml, args.imgsz)
        experiments.append(
            _experiment_record("EVAL", Path(args.weights).stem, True, args.weights, m, args.weights)
        )
        save()

    print(f"\nSaved: {metrics_file}")
    print(f"Saved: {out_dir / 'BANG_IV.md'}")
    print("→ Copy BANG_IV.md vào docs/paper/PAPER_FULL_PLAYBOOK_VI.md § KẾT QUẢ THỰC TẾ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
