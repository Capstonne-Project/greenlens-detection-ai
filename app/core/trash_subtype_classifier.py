"""EfficientNet-B0 trash subtype classifier — Stage 2 of 2-stage pipeline.

Classifies cropped TRASH bbox regions into 7 subtypes:
  CONSTRUCTION | ELECTRONIC | HAZARDOUS | HOUSEHOLD | MEDICAL | ORGANIC | RECYCLABLE
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from app.config import Settings, get_settings

TRASH_SUBTYPES = [
    "CONSTRUCTION",
    "ELECTRONIC",
    "HAZARDOUS",
    "HOUSEHOLD",
    "MEDICAL",
    "ORGANIC",
    "RECYCLABLE",
]

_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]
_CROP_PAD = 4  # extra pixels around bbox for context


class TrashSubtypeClassifier:
    """Lazy-load EfficientNet-B0 fine-tuned to classify TRASH subtypes from cropped bbox regions."""

    __slots__ = ("_attempted_load", "_idx_to_class", "_model", "_settings", "_transform")

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._model: Any | None = None
        self._idx_to_class: dict[int, str] = {}
        self._transform: Any | None = None
        self._attempted_load = False

    def is_loaded(self) -> bool:
        self._ensure_model()
        return self._model is not None

    def _ensure_model(self) -> Any | None:
        if self._attempted_load:
            return self._model
        self._attempted_load = True

        path_str = self._settings.trash_subtype_model_path.strip()
        if not path_str:
            return None

        path = Path(path_str)
        if not path.is_file():
            return None

        try:
            import torch
            import torch.nn as nn
            from torchvision import transforms
            from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

            checkpoint = torch.load(str(path), map_location="cpu", weights_only=True)
            class_to_idx: dict[str, int] = checkpoint["class_to_idx"]
            self._idx_to_class = {v: k for k, v in class_to_idx.items()}
            num_classes = len(class_to_idx)

            model = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
            model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
            model.load_state_dict(checkpoint["state_dict"])
            model.eval()
            self._model = model

            self._transform = transforms.Compose(
                [
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
                ]
            )
        except Exception:
            self._model = None

        return self._model

    def predict_subtype(
        self,
        image: Image.Image,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> tuple[str, float]:
        """Crop bbox from image and classify trash subtype.

        Returns (subtype, confidence). Returns ("UNKNOWN", 0.0) when model
        is not loaded or confidence is below threshold.
        """
        model = self._ensure_model()
        if model is None or self._transform is None:
            return ("UNKNOWN", 0.0)

        try:
            import torch

            iw, ih = image.size
            cx1 = max(0, int(x1) - _CROP_PAD)
            cy1 = max(0, int(y1) - _CROP_PAD)
            cx2 = min(iw, int(x2) + _CROP_PAD)
            cy2 = min(ih, int(y2) + _CROP_PAD)

            if cx2 <= cx1 or cy2 <= cy1:
                return ("UNKNOWN", 0.0)

            crop = image.crop((cx1, cy1, cx2, cy2)).convert("RGB")
            tensor = self._transform(crop).unsqueeze(0)

            with torch.no_grad():
                logits = model(tensor)
                probs = torch.softmax(logits, dim=1)[0]

            top_idx = int(probs.argmax().item())
            top_conf = float(probs[top_idx].item())

            if top_conf < self._settings.trash_subtype_threshold:
                return ("UNKNOWN", round(top_conf, 4))

            subtype = self._idx_to_class.get(top_idx, "UNKNOWN")
            return (subtype, round(top_conf, 4))

        except Exception:
            return ("UNKNOWN", 0.0)


_instance: TrashSubtypeClassifier | None = None


def get_trash_subtype_classifier() -> TrashSubtypeClassifier:
    global _instance
    if _instance is None:
        _instance = TrashSubtypeClassifier()
    return _instance
