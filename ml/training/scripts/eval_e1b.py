#!/usr/bin/env python3
"""
Eval E1b_best.pt on test split and print per-class mAP50 correctly.
Run on Kaggle:
  !python eval_e1b.py
"""

import json
from datetime import UTC, datetime

from ultralytics import YOLO

WEIGHTS = "/kaggle/working/paper_output/E1b_best.pt"
DATA_YAML = "/kaggle/working/paper_output/data.yaml"
IMGSZ = 1280
CLASS_NAMES = ("TRASH", "WATER")

model = YOLO(WEIGHTS)
results = model.val(data=DATA_YAML, split="test", imgsz=IMGSZ, verbose=True)

box = results.box

# ALL metrics
all_map50 = round(float(box.map50), 4)
all_map50_95 = round(float(box.map), 4)
all_p = round(float(box.mp), 4)
all_r = round(float(box.mr), 4)

# Per-class — fix: maps50 for mAP50, maps for mAP50-95
maps50 = list(box.maps50) if (hasattr(box, "maps50") and box.maps50 is not None) else []
maps50_95 = list(box.maps) if (hasattr(box, "maps") and box.maps is not None) else []
p_list = list(box.p) if (hasattr(box, "p") and box.p is not None) else []
r_list = list(box.r) if (hasattr(box, "r") and box.r is not None) else []

per_class = {}
for i, name in enumerate(CLASS_NAMES):
    per_class[name] = {
        "map50": round(float(maps50[i]), 4) if i < len(maps50) else None,
        "map50_95": round(float(maps50_95[i]), 4) if i < len(maps50_95) else None,
        "precision": round(float(p_list[i]), 4) if i < len(p_list) else None,
        "recall": round(float(r_list[i]), 4) if i < len(r_list) else None,
    }

output = {
    "model": "E1b YOLOv8s",
    "weights": WEIGHTS,
    "evaluated_at": datetime.now(UTC).isoformat(),
    "all": {
        "precision": all_p,
        "recall": all_r,
        "map50": all_map50,
        "map50_95": all_map50_95,
    },
    "per_class": per_class,
}

print("\n========== E1b RESULTS ==========")
print(json.dumps(output, indent=2))
print("=================================\n")

print("Table 9 row:")
print(
    f"  E1b YOLOv8s | Yes | "
    f"TRASH P={per_class['TRASH']['precision']} | "
    f"TRASH R={per_class['TRASH']['recall']} | "
    f"TRASH mAP50={per_class['TRASH']['map50']} | "
    f"WATER P={per_class['WATER']['precision']} | "
    f"WATER R={per_class['WATER']['recall']} | "
    f"WATER mAP50={per_class['WATER']['map50']} | "
    f"ALL mAP50={all_map50} | "
    f"ALL mAP50-95={all_map50_95}"
)
