#!/usr/bin/env python3
"""Validate YOLO layout for pollution training (TRASH/WATER/SMOKE).

Usage (from repo root):
  uv run python ml/training/scripts/verify_yolo_dataset.py --root ml/training/data/pollution
"""

from __future__ import annotations

import argparse
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_yolo_line(line: str) -> tuple[int, float, float, float, float] | None:
    parts = line.strip().split()
    if len(parts) != 5:
        return None
    try:
        cid = int(parts[0])
        xs = [float(parts[i]) for i in range(1, 5)]
    except ValueError:
        return None
    return cid, xs[0], xs[1], xs[2], xs[3]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify YOLO dataset layout and class ids.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("ml/training/data/pollution"),
        help="Root folder with images/{train,val} and labels/{train,val}.",
    )
    parser.add_argument("--nc", type=int, default=3, help="Expected number of classes (0..nc-1).")
    args = parser.parse_args()
    root = args.root.resolve()

    issues: list[str] = []
    per_split_class: dict[str, dict[int, int]] = {}
    bbox_total = 0

    for split in ("train", "val"):
        img_dir = root / "images" / split
        lab_dir = root / "labels" / split
        if not img_dir.is_dir():
            issues.append(f"Missing directory: {img_dir}")
            continue
        if not lab_dir.is_dir():
            issues.append(f"Missing directory: {lab_dir}")
            continue

        per_split_class[split] = dict.fromkeys(range(args.nc), 0)
        imgs = [p for p in img_dir.iterdir() if p.suffix.lower() in IMG_EXT]

        for img_path in sorted(imgs):
            lab_path = lab_dir / f"{img_path.stem}.txt"
            if not lab_path.is_file():
                issues.append(f"Missing label for {img_path.name} (expected {lab_path.name})")
                continue
            text = lab_path.read_text(encoding="utf-8").strip()
            if not text:
                issues.append(f"Empty label file: {lab_path}")
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                if not line.strip():
                    continue
                parsed = parse_yolo_line(line)
                if parsed is None:
                    issues.append(f"Bad line {lab_path}:{line_no}: {line!r}")
                    continue
                cid, xc, yc, w, h = parsed
                if cid < 0 or cid >= args.nc:
                    issues.append(
                        f"class {cid} out of range [0,{args.nc - 1}] in {lab_path}:{line_no}"
                    )
                    continue
                for i, v in enumerate((xc, yc, w, h)):
                    if not (0.0 <= v <= 1.0):
                        issues.append(
                            f"coord out of [0,1] in {lab_path}:{line_no} pos {i} ({v}) — check YOLO norm",
                        )
                per_split_class[split][cid] += 1
                bbox_total += 1

        # labels without images
        if lab_dir.is_dir():
            for lab in lab_dir.glob("*.txt"):
                stem = lab.stem
                matches = list(img_dir.glob(f"{stem}.*"))
                has_img = any(p.suffix.lower() in IMG_EXT for p in matches)
                if not has_img:
                    issues.append(f"Orphan label (no image base name): {lab.name}")

    print("Root:", root)
    print(f"Expected classes: 0=TRASH 1=WATER 2=SMOKE (nc={args.nc})")
    print("Total bbox lines:", bbox_total)
    for split, counts in sorted(per_split_class.items()):
        print(f"  [{split}] bbox per class:", dict(counts))

    missing_classes: list[int] = []
    for c in range(args.nc):
        train_c = per_split_class.get("train", {}).get(c, 0)
        val_c = per_split_class.get("val", {}).get(c, 0)
        if train_c == 0 and val_c == 0:
            missing_classes.append(c)

    if missing_classes:
        names = ["TRASH", "WATER", "SMOKE"]
        for c in missing_classes:
            print(
                f"WARN: no examples for class {c} ({names[c] if c < 3 else '?'}) — model will not learn it."
            )

    if issues:
        print(f"\nIssues ({len(issues)}):")
        for msg in issues[:50]:
            print(" -", msg)
        if len(issues) > 50:
            print(f" ... ({len(issues) - 50} more)")
        return 1

    print("\nOK: layout checks passed (no missing pairs / bad lines in scan).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
