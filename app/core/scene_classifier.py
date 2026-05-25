"""EfficientNet-B0 scene classifier for WATER and SMOKE pollution."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from PIL import Image

from app.config import Settings, get_settings

try:
    import torch
    import torch.nn as nn
    from torchvision import transforms
    from torchvision.models import efficientnet_b0

    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TORCH_AVAILABLE = False

_SCENE_CLASSES = ("WATER", "SMOKE", "NEGATIVE")

_INFERENCE_TRANSFORM = None


def _get_transform() -> Any:
    global _INFERENCE_TRANSFORM
    if _INFERENCE_TRANSFORM is None and _TORCH_AVAILABLE:
        _INFERENCE_TRANSFORM = transforms.Compose(
            [
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )
    return _INFERENCE_TRANSFORM


def _build_efficientnet_b0(num_classes: int) -> Any:
    m = efficientnet_b0(weights=None)
    in_features = m.classifier[1].in_features
    m.classifier[1] = nn.Linear(in_features, num_classes)
    return m


class ScenePollutionClassifier:
    """Lazy-load fine-tuned EfficientNet-B0; returns WATER/SMOKE probabilities."""

    __slots__ = ("_attempted_load", "_class_to_idx", "_model", "_settings")

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._model: Any | None = None
        self._class_to_idx: dict[str, int] = {"WATER": 0, "SMOKE": 1, "NEGATIVE": 2}
        self._attempted_load = False

    def is_loaded(self) -> bool:
        self._ensure_model()
        return self._model is not None

    def _ensure_model(self) -> Any | None:
        if self._attempted_load:
            return self._model
        self._attempted_load = True

        if not _TORCH_AVAILABLE:
            return None

        path_str = self._settings.scene_classifier_path
        if not path_str:
            return None

        path = Path(path_str)
        if not path.is_file():
            return None

        ckpt: dict[str, Any] = torch.load(str(path), map_location="cpu", weights_only=True)
        class_to_idx: dict[str, int] = ckpt.get("class_to_idx", self._class_to_idx)
        num_classes = len(class_to_idx)

        m = _build_efficientnet_b0(num_classes)
        m.load_state_dict(ckpt["state_dict"])
        m.eval()

        self._class_to_idx = class_to_idx
        self._model = m
        return m

    def predict_proba(self, image_bytes: bytes) -> dict[str, float]:
        """Return {WATER: float, SMOKE: float}. Returns zeros if model not loaded."""
        model = self._ensure_model()
        if model is None:
            return {"WATER": 0.0, "SMOKE": 0.0}

        transform = _get_transform()
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            rgb = pil_img.convert("RGB")

        tensor = transform(rgb).unsqueeze(0)  # type: ignore[operator]

        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1)[0]

        idx_to_class = {v: k for k, v in self._class_to_idx.items()}
        result = {"WATER": 0.0, "SMOKE": 0.0}
        for idx, prob in enumerate(probs.tolist()):
            cls = idx_to_class.get(idx, "")
            if cls in result:
                result[cls] = round(float(prob), 4)
        return result


_SCENE_CLASSIFIER: ScenePollutionClassifier | None = None


def get_scene_classifier(settings: Settings | None = None) -> ScenePollutionClassifier:
    global _SCENE_CLASSIFIER
    if _SCENE_CLASSIFIER is None:
        _SCENE_CLASSIFIER = ScenePollutionClassifier(settings)
    return _SCENE_CLASSIFIER
