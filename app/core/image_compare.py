"""DINOv2 image embedding + cosine similarity for Tier 2 duplicate detection.

BR-REP-030 / BR-AI-002: compare a new pollution report photo against an existing
candidate. Uses the pretrained DINOv2 backbone (Meta LVD-142M, self-supervised) as a
frozen feature extractor — no training. Isolated from the YOLO detect pipeline.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from app.config import Settings, get_settings
from app.utils.image_decode import decode_image_bytes_to_jpeg


@dataclass
class CompareResult:
    confidence: float
    is_same_scene: bool
    model: str


class ImageCompareService:
    """Lazy-loaded DINOv2 embedder. Its own singleton — does not touch YOLO state."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._model: Any | None = None
        self._processor: Any | None = None
        self._attempted_load = False

    def _ensure_model(self) -> Any | None:
        if self._attempted_load:
            return self._model
        self._attempted_load = True
        try:
            from transformers import AutoImageProcessor, AutoModel
        except ImportError:  # pragma: no cover - dependency missing
            return None
        try:
            name = self._settings.compare_model_name
            self._processor = AutoImageProcessor.from_pretrained(name)  # type: ignore[no-untyped-call]
            model = AutoModel.from_pretrained(name)
            model.eval()
            self._model = model
        except Exception:  # pragma: no cover - download/load failure
            self._model = None
            self._processor = None
        return self._model

    def model_is_loaded(self) -> bool:
        return self._ensure_model() is not None

    def _embed(self, image_bytes: bytes) -> Any:
        """Decode bytes -> DINOv2 [CLS] embedding, L2-normalized. Returns a 1xD tensor."""
        import torch

        model = self._ensure_model()
        if model is None or self._processor is None:
            raise RuntimeError("DINOv2 compare model is not available.")

        jpeg_bytes, _ = decode_image_bytes_to_jpeg(image_bytes)
        from PIL import Image

        with Image.open(io.BytesIO(jpeg_bytes)) as im:
            image = im.convert("RGB")
            inputs = self._processor(images=image, return_tensors="pt")

        with torch.no_grad():
            outputs = model(**inputs)

        embedding = outputs.last_hidden_state[:, 0, :]  # [CLS] token
        return torch.nn.functional.normalize(embedding, dim=-1)

    def compare_bytes(self, image_a: bytes, image_b: bytes) -> CompareResult:
        """Compare two images. Blocking — call via asyncio.to_thread from the router."""
        import torch

        emb_a = self._embed(image_a)
        emb_b = self._embed(image_b)
        score = torch.nn.functional.cosine_similarity(emb_a, emb_b).item()
        score = max(0.0, min(1.0, score))
        threshold = self._settings.compare_threshold
        return CompareResult(
            confidence=round(score, 4),
            is_same_scene=score >= threshold,
            model=self._settings.compare_model_version,
        )
