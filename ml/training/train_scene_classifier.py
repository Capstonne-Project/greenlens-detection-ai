#!/usr/bin/env python3
"""
Fine-tune EfficientNet-B0 for WATER / SMOKE scene classification.

Dataset layout (relative to --data-root):
  images/train/WATER/    *.jpg / *.png
  images/train/SMOKE/
  images/train/NEGATIVE/
  images/val/WATER/      (optional — auto-split from train if missing)
  images/val/SMOKE/
  images/val/NEGATIVE/

Output:
  ml/weights/scene_classifier.pt   — set SCENE_CLASSIFIER_PATH in .env

Usage (from repo root):
  uv run python ml/training/train_scene_classifier.py --data-root ml/training/data/scene
  uv run python ml/training/train_scene_classifier.py --epochs 20 --batch-size 32
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_CLASSES = ["WATER", "SMOKE", "NEGATIVE"]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fine-tune EfficientNet-B0 for scene pollution (WATER/SMOKE)."
    )
    p.add_argument(
        "--data-root",
        default=str(_PROJECT_ROOT / "ml" / "training" / "data" / "scene"),
        help="Root with images/train/{WATER,SMOKE,NEGATIVE}/ sub-folders.",
    )
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument(
        "--workers",
        type=int,
        default=0,
        help="DataLoader workers (0 = main thread, safe on Windows).",
    )
    p.add_argument(
        "--val-fraction",
        type=float,
        default=0.15,
        help="If images/val/ is missing, split this fraction from train for validation.",
    )
    p.add_argument(
        "--output",
        default=str(_PROJECT_ROOT / "ml" / "weights" / "scene_classifier.pt"),
        help="Where to save the best checkpoint.",
    )
    p.add_argument(
        "--log-every-batches",
        type=int,
        default=10,
        metavar="N",
        help="Print train/val progress every N batches (set 1 for every batch; larger = quieter).",
    )
    return p.parse_args()


def _log(msg: str) -> None:
    print(msg, flush=True)


def _build_val_split(train_dir: Path, val_dir: Path, fraction: float) -> None:
    """Move a random fraction of each class from train_dir to val_dir."""
    for cls in _CLASSES:
        src = train_dir / cls
        dst = val_dir / cls
        if not src.is_dir():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        images = [f for f in src.iterdir() if f.is_file()]
        n_val = max(1, int(len(images) * fraction))
        for img in random.sample(images, min(n_val, len(images))):
            shutil.move(str(img), dst / img.name)


def main() -> int:
    args = _parse_args()

    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader
        from torchvision import transforms
        from torchvision.datasets import ImageFolder
        from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0
    except ImportError as exc:
        raise SystemExit(
            f"torch / torchvision not installed. Run: uv add torch torchvision\n{exc}"
        ) from exc

    data_root = Path(args.data_root)
    train_dir = data_root / "images" / "train"
    val_dir = data_root / "images" / "val"

    if not train_dir.is_dir():
        raise SystemExit(
            f"Missing training folder: {train_dir}\n"
            "Create images/train/WATER/, images/train/SMOKE/, images/train/NEGATIVE/ and add images."
        )

    # Auto-build val split if val/ doesn't have all classes populated.
    val_has_data = val_dir.is_dir() and any(
        (val_dir / cls).is_dir() and any((val_dir / cls).iterdir())
        for cls in _CLASSES
        if (val_dir / cls).is_dir()
    )
    if not val_has_data:
        _log(
            f"[info] No val split found — splitting {args.val_fraction:.0%} from train automatically."
        )
        _build_val_split(train_dir, val_dir, args.val_fraction)

    train_tf = transforms.Compose(
        [
            transforms.RandomResizedCrop(224, scale=(0.7, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    val_tf = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    train_ds = ImageFolder(str(train_dir), transform=train_tf)
    val_ds = ImageFolder(str(val_dir), transform=val_tf)

    if len(train_ds) == 0:
        raise SystemExit(
            "Training dataset is empty. Add images under images/train/{WATER,SMOKE,NEGATIVE}/."
        )

    _log(f"[info] train={len(train_ds)} samples | val={len(val_ds)} samples")
    _log(f"[info] class_to_idx = {train_ds.class_to_idx}")

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        pin_memory=False,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=False,
    )
    n_train_batches = len(train_loader)
    n_val_batches = len(val_loader)
    log_every = max(1, args.log_every_batches)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    _log(f"EfficientNet-B0 Scene Classifier  classes={len(train_ds.classes)}  device={device}")
    _log(f"{'':>10}  {'train':>6}  {'val':>6}  samples")
    _log(f"{'dataset':>10}  {len(train_ds):>6}  {len(val_ds):>6}")
    _log(f"{'batches':>10}  {n_train_batches:>6}  {n_val_batches:>6}")
    _log(f"optimizer  AdamW  lr={args.lr}  weight_decay=1e-4  scheduler=CosineAnnealing")
    _log("")
    _log(
        "[info] loading ImageNet pretrained EfficientNet-B0 "
        "(first run may print many download % lines — that is normal)."
    )

    model = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, len(train_ds.classes))
    model = model.to(device)

    _log("[info] backbone ready")
    _log("")
    _log(f"{'Epoch':>8}  {'train_loss':>10}  {'val_loss':>8}  {'val_acc':>7}  best")
    _log(f"{'-'*8}  {'-'*10}  {'-'*8}  {'-'*7}  {'-'*4}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0
    best_state: dict | None = None

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        # ---- train ----
        model.train()
        train_loss = 0.0
        running_sum = 0.0
        running_n = 0
        for batch_idx, (images, labels) in enumerate(train_loader, start=1):
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = criterion(model(images), labels)
            loss.backward()
            optimizer.step()
            bs = len(images)
            train_loss += loss.item() * bs
            running_sum += loss.item() * bs
            running_n += bs
            if batch_idx == 1 or batch_idx == n_train_batches or batch_idx % log_every == 0:
                pct = batch_idx / n_train_batches
                bar_w = 20
                filled = int(bar_w * pct)
                bar = "=" * filled + "-" * (bar_w - filled)
                _log(
                    f"  train {epoch}/{args.epochs}  "
                    f"[{bar}] {batch_idx}/{n_train_batches}  "
                    f"loss={running_sum / max(running_n, 1):.4f}"
                )
        scheduler.step()

        # ---- val ----
        model.eval()
        correct = total = 0
        val_loss = 0.0
        with torch.no_grad():
            for batch_idx, (images, labels) in enumerate(val_loader, start=1):
                images, labels = images.to(device), labels.to(device)
                out = model(images)
                bs = len(images)
                val_loss += criterion(out, labels).item() * bs
                correct += (out.argmax(1) == labels).sum().item()
                total += len(labels)
                if batch_idx == 1 or batch_idx == n_val_batches or batch_idx % log_every == 0:
                    pct = batch_idx / n_val_batches
                    bar_w = 20
                    filled = int(bar_w * pct)
                    bar = "=" * filled + "-" * (bar_w - filled)
                    _log(
                        f"  val   {epoch}/{args.epochs}  "
                        f"[{bar}] {batch_idx}/{n_val_batches}  "
                        f"acc={correct / max(total, 1):.4f}"
                    )

        val_acc = correct / total if total else 0.0
        is_best = val_acc >= best_val_acc
        if is_best:
            best_val_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        _log(
            f"{epoch:>5}/{args.epochs}  "
            f"{train_loss/len(train_ds):>10.4f}  "
            f"{val_loss/max(total,1):>8.4f}  "
            f"{val_acc:>7.4f}  "
            f"{'  *' if is_best else ''}"
        )
        _log("")

    if best_state is None:
        raise SystemExit("Training produced no valid checkpoint.")

    import torch as _torch

    _torch.save(
        {"state_dict": best_state, "class_to_idx": train_ds.class_to_idx},
        str(output_path),
    )
    _log(f"{'='*60}")
    _log("[DONE] Training finished!")
    _log(f"{'='*60}")
    _log(f"  best_val_acc : {best_val_acc:.4f}")
    _log(f"  checkpoint   : {output_path.resolve()}")
    _log("")
    _log("--- Paste vao .env ---------------------------------")
    _log(f"  SCENE_CLASSIFIER_PATH={output_path}")
    _log(f"{'='*60}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
