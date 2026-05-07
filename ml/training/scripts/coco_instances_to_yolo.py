#!/usr/bin/env python3
"""Convert COCO *instances* annotations to YOLO txt labels (one txt per image).

Requires: images on disk + COCO JSON (categories / images / annotations).

Map COCO category IDs to pollution class 0..3 via a small JSON file:

  {
    "1": 0,
    "15": 0
  }

Keys = COCO category id (string or int in file), values = target id 0-3.

Usage:
  uv run python ml/training/scripts/coco_instances_to_yolo.py \\
      --json path/to/instances.json \\
      --images-dir path/to/images \\
      --out-labels-dir path/to/out/labels/train \\
      --map-json path/to/map.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_mapping(path: Path) -> dict[int, int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[int, int] = {}
    for k, v in raw.items():
        out[int(k)] = int(v)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, required=True, help="COCO instances JSON.")
    parser.add_argument(
        "--images-dir",
        type=Path,
        required=True,
        help="Folder with image files named as in COCO 'file_name'.",
    )
    parser.add_argument(
        "--out-labels-dir",
        type=Path,
        required=True,
        help="Output directory for *.txt YOLO labels (created if missing).",
    )
    parser.add_argument(
        "--map-json", type=Path, required=True, help="category_id -> pollution class 0-3."
    )
    args = parser.parse_args()

    coco = json.loads(args.json.read_text(encoding="utf-8"))
    cat_map = load_mapping(args.map_json)

    images = {img["id"]: img for img in coco.get("images", [])}
    anns_by_image: dict[int, list[dict]] = {}
    for ann in coco.get("annotations", []):
        if ann.get("iscrowd", 0) == 1:
            continue
        iid = ann["image_id"]
        anns_by_image.setdefault(iid, []).append(ann)

    args.out_labels_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped_cats: set[int] = set()
    missing_imgs = 0

    for iid, meta in sorted(images.items()):
        file_name = meta["file_name"]
        w_img = float(meta["width"])
        h_img = float(meta["height"])
        img_path = args.images_dir / file_name
        if not img_path.is_file():
            missing_imgs += 1
            continue

        stem = Path(file_name).stem
        out_txt = args.out_labels_dir / f"{stem}.txt"
        lines: list[str] = []

        for ann in anns_by_image.get(iid, []):
            cid_coco = int(ann["category_id"])
            if cid_coco not in cat_map:
                skipped_cats.add(cid_coco)
                continue
            cls = cat_map[cid_coco]
            if cls < 0 or cls > 3:
                raise SystemExit(f"Map target must be 0-3, got {cls} for coco cat {cid_coco}")

            bx, by, bw, bh = ann["bbox"]
            x_c = (bx + bw / 2.0) / w_img
            y_c = (by + bh / 2.0) / h_img
            ww = bw / w_img
            hh = bh / h_img
            for v in (x_c, y_c, ww, hh):
                if not (0.0 <= v <= 1.0):
                    # clip slightly out of bounds numerically
                    pass
            lines.append(f"{cls} {x_c:.6f} {y_c:.6f} {ww:.6f} {hh:.6f}")

        out_txt.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        written += 1

    print("Images in COCO:", len(images))
    print("Label files written:", written)
    print("COCO images missing on disk:", missing_imgs)
    if skipped_cats:
        print("COCO category ids skipped (not in map):", sorted(skipped_cats))
    print("Output:", args.out_labels_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
