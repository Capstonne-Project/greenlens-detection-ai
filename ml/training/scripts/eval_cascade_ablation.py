#!/usr/bin/env python3
"""
GreenLens — Cascade Ablation Script (Table 10).

Evaluates 4 cascade configurations at image level:
  Config A: Stage 1 only (YOLO)
  Config B: Stage 1 + 2, evidence-gating (proposed)
  Config C: Stage 1 + 2, naive fusion (scene overrides)
  Config D: Full cascade (Stage 1 + 2 + 3, evidence-gating)

Metrics: image-level Precision, Recall, F1 for WATER and TRASH detection.

Usage:
  pip install ultralytics torch torchvision pillow
  python eval_cascade_ablation.py

Outputs Table 10 numbers to console.
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

# ── Paths (override via CLI args) ────────────────────────────────────────────
BASE = Path(__file__).parent.parent.parent.parent  # project root (scripts/training/ml/project)
YOLO_W = BASE / "ml/weights/E1_best.pt"
SCENE_W = BASE / "ml/weights/scene_classifier.pt"
SUBTYPE_W = BASE / "ml/weights/trash_subtype_classifier.pt"

# Thresholds (from config.py)
YOLO_CONF = 0.30  # relevance_min_confidence
SCENE_THRESH = 0.45  # scene_classifier_threshold
SUBTYPE_THRESH = 0.40

SCENE_CLASSES = ["NEGATIVE", "SMOKE", "WATER"]  # adjust if different
WATER_IDX = SCENE_CLASSES.index("WATER") if "WATER" in SCENE_CLASSES else 2

# ── Helpers ───────────────────────────────────────────────────────────────────


def load_scene_classifier(weights_path: Path, num_classes: int = 3):
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    ckpt = torch.load(weights_path, map_location="cpu", weights_only=False)
    if isinstance(ckpt, dict) and "state_dict" in ckpt:
        state = ckpt["state_dict"]
    elif isinstance(ckpt, dict) and "model_state_dict" in ckpt:
        state = ckpt["model_state_dict"]
    else:
        state = ckpt
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def scene_prob_water(model, img_path: Path, transform) -> float:
    img = Image.open(img_path).convert("RGB")
    t = transform(img).unsqueeze(0)
    with torch.no_grad():
        logits = model(t)
        probs = torch.softmax(logits, dim=1)[0]
    return float(probs[WATER_IDX])


def gt_classes(lbl_path: Path) -> set[int]:
    """Return set of class IDs present in label file."""
    if not lbl_path.is_file():
        return set()
    classes = set()
    for line in lbl_path.read_text().strip().splitlines():
        if line.strip():
            classes.add(int(line.split()[0]))
    return classes


def pr_f1(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return round(p, 4), round(r, 4), round(f, 4)


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GreenLens Cascade Ablation — Table 10")
    parser.add_argument(
        "--data-dir",
        default=r"D:\CapsoneProject\DATASETFINAL\TOTAL\datasetfinal",
        help="Root of your dataset (must contain images/<split> and labels/<split>)",
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=["test", "val"],
        help="Which split to evaluate (default: test)",
    )
    parser.add_argument(
        "--yolo-weights", default=str(YOLO_W), help=f"Path to E1_best.pt (default: {YOLO_W})"
    )
    parser.add_argument(
        "--scene-weights",
        default=str(SCENE_W),
        help=f"Path to scene_classifier.pt (default: {SCENE_W})",
    )
    args = parser.parse_args()

    data_root = Path(args.data_dir)
    img_dir = data_root / "images" / args.split
    lbl_dir = data_root / "labels" / args.split

    if not img_dir.is_dir():
        sys.exit(f"ERROR: images/{args.split} not found in {data_root}\n" f"  Expected: {img_dir}")
    if not lbl_dir.is_dir():
        sys.exit(f"ERROR: labels/{args.split} not found in {data_root}\n" f"  Expected: {lbl_dir}")

    try:
        from ultralytics import YOLO
    except ImportError:
        sys.exit("pip install ultralytics first")

    print("Loading models...")
    yolo = YOLO(args.yolo_weights)

    scene_w = Path(args.scene_weights)
    scene_model = None
    if scene_w.is_file():
        try:
            scene_model = load_scene_classifier(scene_w)
            print(f"  Scene classifier loaded: {scene_w.name}")
        except Exception as e:
            print(f"  WARNING: could not load scene classifier: {e}")
    else:
        print(f"  WARNING: scene classifier not found at {scene_w}")

    tf = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )

    images = sorted(img_dir.glob("*.*"))
    print(f"\nEvaluating on {len(images)} images from {data_root.name}/{args.split}...\n")

    # counters: [config_A, config_B, config_C, config_D]
    # each: {TRASH: {tp,fp,fn}, WATER: {tp,fp,fn}}
    configs = ["A_stage1_only", "B_evidence_gating", "C_naive_fusion", "D_full_cascade"]
    stats = {c: {cls: {"tp": 0, "fp": 0, "fn": 0} for cls in ["TRASH", "WATER"]} for c in configs}

    for img_path in images:
        lbl_path = lbl_dir / (img_path.stem + ".txt")
        gt = gt_classes(lbl_path)
        gt_trash = 0 in gt
        gt_water = 1 in gt

        # ── YOLO inference ────────────────────────────────────────────────────
        res = yolo.predict(str(img_path), conf=YOLO_CONF, verbose=False)[0]
        yolo_trash = any(int(b.cls) == 0 for b in res.boxes) if res.boxes else False
        yolo_water = any(int(b.cls) == 1 for b in res.boxes) if res.boxes else False
        yolo_any = yolo_trash or yolo_water

        # ── Scene classifier ──────────────────────────────────────────────────
        scene_water = False
        if scene_model is not None:
            p_water = scene_prob_water(scene_model, img_path, tf)
            scene_water = p_water >= SCENE_THRESH

        # ── Config A: Stage 1 only ────────────────────────────────────────────
        pred_trash_a = yolo_trash
        pred_water_a = yolo_water

        # ── Config B: evidence-gating (scene supplements ONLY if ≥1 YOLO box) ─
        pred_trash_b = yolo_trash
        pred_water_b = yolo_water or (scene_water and yolo_any)

        # ── Config C: naive fusion (scene can fire even with no YOLO boxes) ───
        pred_trash_c = yolo_trash
        pred_water_c = yolo_water or scene_water  # no gating

        # ── Config D: full cascade (same as B + subtype, water same as B) ─────
        pred_trash_d = yolo_trash
        pred_water_d = pred_water_b  # subtype doesn't affect water detection

        for cfg, pt, pw in [
            ("A_stage1_only", pred_trash_a, pred_water_a),
            ("B_evidence_gating", pred_trash_b, pred_water_b),
            ("C_naive_fusion", pred_trash_c, pred_water_c),
            ("D_full_cascade", pred_trash_d, pred_water_d),
        ]:
            for cls_name, pred, gt_flag in [("TRASH", pt, gt_trash), ("WATER", pw, gt_water)]:
                s = stats[cfg][cls_name]
                if pred and gt_flag:
                    s["tp"] += 1
                elif pred and not gt_flag:
                    s["fp"] += 1
                elif not pred and gt_flag:
                    s["fn"] += 1

    # ── Print Table 10 ────────────────────────────────────────────────────────
    print("=" * 80)
    print("TABLE 10 — Cascade Ablation (image-level detection)")
    print("=" * 80)
    header = f"{'Configuration':<30} {'WATER P':>8} {'WATER R':>8} {'WATER F1':>9} {'TRASH P':>8} {'TRASH R':>8} {'TRASH F1':>9}"
    print(header)
    print("-" * 80)

    labels = {
        "A_stage1_only": "Stage 1 only (YOLO)",
        "B_evidence_gating": "Stage 1+2 evidence-gating ★",
        "C_naive_fusion": "Stage 1+2 naive fusion",
        "D_full_cascade": "Full cascade (all 3 stages)",
    }

    for cfg in configs:
        s = stats[cfg]
        wp, wr, wf = pr_f1(s["WATER"]["tp"], s["WATER"]["fp"], s["WATER"]["fn"])
        tp2, tr, tf2 = pr_f1(s["TRASH"]["tp"], s["TRASH"]["fp"], s["TRASH"]["fn"])
        label = labels[cfg]
        print(f"{label:<30} {wp:>8.4f} {wr:>8.4f} {wf:>9.4f} {tp2:>8.4f} {tr:>8.4f} {tf2:>9.4f}")

    print("=" * 80)
    print("\n★ = proposed method\n")
    print("Copy numbers above into Table 10 of the paper.")
    print("Note: metrics are image-level (does system detect class in image?),")
    print("      not bounding-box mAP50 — add this note in paper footnote.\n")


if __name__ == "__main__":
    main()
