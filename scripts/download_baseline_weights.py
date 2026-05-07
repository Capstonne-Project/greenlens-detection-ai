#!/usr/bin/env python3
"""Fetch Ultralytics pretrained YOLOv8 nano .pt into ml/weights/yolov8n.pt.

Baseline uses COCO class names — your app maps only TRASH/WATER/SMOKE/CHEMICAL,
so predictions may stay empty until you fine-tune on pollution data or extend mapping.

Usage:
    uv run python scripts/download_baseline_weights.py

Then set MODEL_PATH=ml/weights/yolov8n.pt (default) and CLASSIFY_DEMO_MODE=false for real inference.
"""

from pathlib import Path

import httpx

# Official Ultralytics hub assets (nano detection)
_WEIGHT_URL = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt"


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    dest = root / "ml" / "weights" / "yolov8n.pt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        print(f"Skip download — already exists: {dest}")
        return 0
    print(f"Downloading {_WEIGHT_URL}")
    print(f"Destination: {dest}")
    timeout = httpx.Timeout(600.0, connect=60.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(_WEIGHT_URL)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    print("Done.")
    print(
        "\nRemember: pretrained COCO classes do not match pollution labels; "
        "train a custom checkpoint for TRASH/WATER/SMOKE/CHEMICAL (see docs/AI_Service_Development_Plan.md Phase 3).",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
