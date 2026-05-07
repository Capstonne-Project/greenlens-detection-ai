"""YOLO-based pollution *scene* analysis: types + relevance + severity (not SKU-level trash)."""

from __future__ import annotations

import io
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from app.config import Settings, get_settings
from app.core.report_image_relevance import classify_image_relevance
from app.core.severity_estimator import severity_from_pollution_coverage

try:
    from ultralytics import YOLO

except ImportError:  # pragma: no cover
    YOLO = None  # type: ignore[misc, assignment]


POLLUTION_CLASS_CODES = frozenset({"TRASH", "WATER", "SMOKE", "CHEMICAL"})

_CLASS_SYNONYMS: dict[str, str] = {
    "GARBAGE": "TRASH",
    "WASTE": "TRASH",
    "RUBBISH": "TRASH",
    "LITTER": "TRASH",
    "SEWAGE": "WATER",
    "WASTEWATER": "WATER",
    "EFFLUENT": "WATER",
    "SMOG": "SMOKE",
    "PLUME": "SMOKE",
    "AIR_POLLUTION": "SMOKE",
    "CHEM_SPILL": "CHEMICAL",
    "PESTICIDE": "CHEMICAL",
}


def _normalize_pollution_code(raw: str | None) -> str | None:
    if raw is None:
        return None

    u = raw.strip().upper().replace(" ", "_").replace("-", "_")

    if u in POLLUTION_CLASS_CODES:
        return u

    return _CLASS_SYNONYMS.get(u)


@dataclass(frozen=True)
class ClassificationResult:
    """

    Aggregate *scene-level* inference for pollution reporting.



    ``predictions`` holds per-category evidence (from detector aggregation), not

    individual litter SKUs.

    """

    predictions: list[dict[str, Any]]

    primary_class: str | None

    confidence: float

    action: str

    inference_time_ms: float

    model_version: str

    noise_supported: bool

    severity: str

    pollution_coverage_ratio: float

    image_relevance: str


def _demo_result_when_no_model(settings: Settings, elapsed_ms: float) -> ClassificationResult:
    """Synthetic scene for QA — no detector weights."""

    demo_conf = 0.72

    cov = 0.12

    return ClassificationResult(
        predictions=[{"class": "TRASH", "confidence": demo_conf, "bbox_count": 2}],
        primary_class="TRASH",
        confidence=demo_conf,
        action="SUGGEST",
        inference_time_ms=round(elapsed_ms, 2),
        model_version=f"{settings.model_version}+demo-no-weights",
        noise_supported=False,
        severity=severity_from_pollution_coverage(
            cov,
            thr_low=settings.severity_cover_low_below,
            thr_med=settings.severity_cover_medium_below,
            thr_high=settings.severity_cover_high_below,
        ),
        pollution_coverage_ratio=round(min(cov, 1.0), 6),
        image_relevance="POLLUTION_LIKELY",
    )


def _stub_empty(settings: Settings, elapsed_ms: float) -> ClassificationResult:
    return ClassificationResult(
        predictions=[],
        primary_class=None,
        confidence=0.0,
        action="KEEP_USER_CHOICE",
        inference_time_ms=round(elapsed_ms, 2),
        model_version=settings.model_version,
        noise_supported=False,
        severity="LOW",
        pollution_coverage_ratio=0.0,
        image_relevance="NOT_POLLUTION_OR_UNRELATED",
    )


class PollutionClassifier:
    """Lazy-load Ultralytics detector; exposes scene-centric fields for APIs."""

    __slots__ = ("_attempted_load", "_model", "_settings")

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

        self._model: Any | None = None

        self._attempted_load = False

    def model_is_loaded(self) -> bool:
        self._ensure_model()

        return self._model is not None

    def _ensure_model(self) -> Any | None:
        if self._attempted_load:
            return self._model

        self._attempted_load = True

        if YOLO is None:
            return None

        path = Path(self._settings.model_path)

        if not path.is_file():
            return None

        self._model = YOLO(str(path))

        return self._model

    def classify_bytes(self, image_bytes: bytes) -> ClassificationResult:
        settings = self._settings

        version = settings.model_version

        t0 = time.perf_counter()

        noise_supported = False

        model = self._ensure_model()

        if model is None:
            ms = (time.perf_counter() - t0) * 1000

            if settings.classify_demo_mode:
                return _demo_result_when_no_model(settings, ms)

            return _stub_empty(settings, ms)

        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            rgb = pil_img.convert("RGB")

        iw, ih = rgb.size

        img_area = float(iw * ih) if iw and ih else 1.0

        results = model.predict(source=rgb, verbose=False)[0]

        names: dict[int, str] = results.names if hasattr(results, "names") else {}

        class_boxes: defaultdict[str, int] = defaultdict(int)

        class_best_conf: defaultdict[str, float] = defaultdict(float)

        boxes = results.boxes

        raw_detector_boxes = int(len(boxes)) if boxes is not None else 0

        coverage_sum = 0.0

        mapped_pollution_boxes = 0

        max_mapped_confidence = 0.0

        if boxes is not None and len(boxes):
            for box in boxes:
                conf = float(box.conf.item()) if box.conf is not None else 0.0

                cls_id = int(box.cls.item()) if box.cls is not None else -1

                raw_name = names.get(cls_id, str(cls_id))

                code = _normalize_pollution_code(raw_name)

                if box.xyxy is not None:
                    xy = box.xyxy[0]

                    xc1 = float(xy[0].item())

                    yc1 = float(xy[1].item())

                    xc2 = float(xy[2].item())

                    yc2 = float(xy[3].item())

                    box_area = max(0.0, xc2 - xc1) * max(0.0, yc2 - yc1)

                    area_frac = box_area / img_area

                else:
                    area_frac = 0.0

                if code is None:
                    continue

                mapped_pollution_boxes += 1

                max_mapped_confidence = max(max_mapped_confidence, conf)

                coverage_sum += area_frac

                class_boxes[code] += 1

                class_best_conf[code] = max(class_best_conf[code], conf)

        coverage_ratio = min(float(coverage_sum), 1.0)

        predictions: list[dict[str, Any]] = [
            {
                "class": cls,
                "confidence": round(class_best_conf[cls], 4),
                "bbox_count": count,
            }
            for cls, count in sorted(
                class_boxes.items(),
                key=lambda kv: (-kv[1], -class_best_conf[kv[0]]),
            )
        ]

        primary_class: str | None = predictions[0]["class"] if predictions else None

        confidence = float(predictions[0]["confidence"]) if predictions else 0.0

        if confidence >= settings.classification_confidence_auto:
            action = "AUTO_FILL"

        elif confidence >= settings.classification_confidence_suggest_low:
            action = "SUGGEST"

        else:
            action = "KEEP_USER_CHOICE"

        severity = severity_from_pollution_coverage(
            coverage_ratio,
            thr_low=settings.severity_cover_low_below,
            thr_med=settings.severity_cover_medium_below,
            thr_high=settings.severity_cover_high_below,
        )

        image_relevance = classify_image_relevance(
            mapped_pollution_boxes=mapped_pollution_boxes,
            raw_detector_boxes=raw_detector_boxes,
            max_mapped_confidence=max_mapped_confidence,
            relevance_min_confidence=settings.relevance_min_confidence,
        )

        if image_relevance != "POLLUTION_LIKELY" and mapped_pollution_boxes == 0:
            action = "KEEP_USER_CHOICE"

        ms = (time.perf_counter() - t0) * 1000

        return ClassificationResult(
            predictions=predictions,
            primary_class=primary_class,
            confidence=round(confidence, 4),
            action=action,
            inference_time_ms=round(ms, 2),
            model_version=version,
            noise_supported=noise_supported,
            severity=severity,
            pollution_coverage_ratio=round(coverage_ratio, 6),
            image_relevance=image_relevance,
        )
