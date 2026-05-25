"""YOLO + scene classifier parallel pollution analysis: types + relevance + severity."""

from __future__ import annotations

import io
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
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


POLLUTION_CLASS_CODES = frozenset({"TRASH", "WATER", "SMOKE"})

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
    """Aggregate *scene-level* inference for pollution reporting."""

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

    yolo_active: bool = False

    scene_classifier_active: bool = False

    detector_model_version: str | None = None

    scene_model_version: str | None = None

    scene_scores: dict[str, float] | None = None


def _format_model_version(
    settings: Settings,
    *,
    yolo_loaded: bool,
    scene_loaded: bool,
) -> str:
    """Composite audit string (BR-AI-005): YOLO + scene status in one field."""
    yolo_part = settings.model_version if yolo_loaded else "yolo:off"
    if scene_loaded:
        scene_tag = settings.scene_classifier_version.strip() or "loaded"
        scene_part = f"scene:{scene_tag}"
    else:
        scene_part = "scene:off"
    return f"{yolo_part}|{scene_part}"


def _demo_result_when_no_model(settings: Settings, elapsed_ms: float) -> ClassificationResult:
    """Synthetic scene for QA — no detector weights."""

    demo_conf = 0.72

    cov = 0.12

    return ClassificationResult(
        predictions=[{"class": "TRASH", "confidence": demo_conf, "bbox_count": 2, "boxes": []}],
        primary_class="TRASH",
        confidence=demo_conf,
        action="SUGGEST",
        inference_time_ms=round(elapsed_ms, 2),
        model_version=f"{settings.model_version}+demo-no-weights|scene:off",
        noise_supported=False,
        severity=severity_from_pollution_coverage(
            cov,
            thr_low=settings.severity_cover_low_below,
            thr_med=settings.severity_cover_medium_below,
            thr_high=settings.severity_cover_high_below,
        ),
        pollution_coverage_ratio=round(min(cov, 1.0), 6),
        image_relevance="POLLUTION_LIKELY",
        yolo_active=False,
        scene_classifier_active=False,
        detector_model_version=None,
        scene_model_version=None,
        scene_scores=None,
    )


def _stub_empty(settings: Settings, elapsed_ms: float) -> ClassificationResult:
    return ClassificationResult(
        predictions=[],
        primary_class=None,
        confidence=0.0,
        action="KEEP_USER_CHOICE",
        inference_time_ms=round(elapsed_ms, 2),
        model_version=_format_model_version(settings, yolo_loaded=False, scene_loaded=False),
        noise_supported=False,
        severity="LOW",
        pollution_coverage_ratio=0.0,
        image_relevance="NOT_POLLUTION_OR_UNRELATED",
        yolo_active=False,
        scene_classifier_active=False,
        detector_model_version=None,
        scene_model_version=None,
        scene_scores=None,
    )


def _merge_yolo_and_scene(
    yolo_predictions: list[dict[str, Any]],
    scene_proba: dict[str, float],
    scene_threshold: float,
    raw_detector_boxes: int = 0,
) -> list[dict[str, Any]]:
    """Merge YOLO bbox results with scene classifier probabilities.

    YOLO is authoritative for all 4 classes (bbox evidence takes priority).
    Scene classifier supplements WATER/SMOKE only when YOLO already detected at
    least one object — this prevents scene from solo-deciding when the image has
    no detectable objects at all (e.g. a trash pile YOLO missed).
    """
    merged: dict[str, dict[str, Any]] = {}

    # Accept all 4 classes from YOLO — scene-level context is inferred separately.
    for pred in yolo_predictions:
        merged[pred["class"]] = pred

    # Scene classifier only supplements when YOLO already saw something.
    # If YOLO found zero boxes, scene alone is not reliable enough to assert a class.
    if raw_detector_boxes > 0:
        for cls in ("WATER", "SMOKE"):
            if cls not in merged:
                prob = scene_proba.get(cls, 0.0)
                if prob >= scene_threshold:
                    merged[cls] = {
                        "class": cls,
                        "confidence": round(prob, 4),
                        "bbox_count": 0,
                        "boxes": [],
                    }

    return sorted(merged.values(), key=lambda p: -p["confidence"])


class PollutionClassifier:
    """Lazy-load Ultralytics detector + EfficientNet-B0 scene classifier; runs in parallel."""

    __slots__ = ("_attempted_load", "_model", "_scene_clf", "_settings")

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

        self._model: Any | None = None
        self._attempted_load = False

        # Lazy-import to avoid circular
        from app.core.scene_classifier import ScenePollutionClassifier

        self._scene_clf = ScenePollutionClassifier(self._settings)

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

    def _run_yolo(self, image_bytes: bytes) -> tuple[list[dict[str, Any]], float, int, int, float]:
        """Run YOLO inference; return (predictions, coverage_ratio, mapped_boxes, raw_boxes, max_conf)."""
        model = self._ensure_model()

        if model is None:
            return [], 0.0, 0, 0, 0.0

        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            rgb = pil_img.convert("RGB")

        iw, ih = rgb.size
        img_area = float(iw * ih) if iw and ih else 1.0

        results = model.predict(source=rgb, verbose=False, imgsz=1280)[0]

        names: dict[int, str] = results.names if hasattr(results, "names") else {}

        class_boxes: defaultdict[str, int] = defaultdict(int)
        class_best_conf: defaultdict[str, float] = defaultdict(float)
        class_raw_boxes: defaultdict[str, list[dict[str, float]]] = defaultdict(list)
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

                xc1 = yc1 = xc2 = yc2 = 0.0
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
                class_raw_boxes[code].append(
                    {
                        "x1": round(xc1, 2),
                        "y1": round(yc1, 2),
                        "x2": round(xc2, 2),
                        "y2": round(yc2, 2),
                        "confidence": round(conf, 4),
                    }
                )

        coverage_ratio = min(float(coverage_sum), 1.0)

        predictions: list[dict[str, Any]] = [
            {
                "class": cls,
                "confidence": round(class_best_conf[cls], 4),
                "bbox_count": count,
                "boxes": class_raw_boxes[cls],
            }
            for cls, count in sorted(
                class_boxes.items(),
                key=lambda kv: (-kv[1], -class_best_conf[kv[0]]),
            )
        ]

        return (
            predictions,
            coverage_ratio,
            mapped_pollution_boxes,
            raw_detector_boxes,
            max_mapped_confidence,
        )

    def classify_bytes(self, image_bytes: bytes) -> ClassificationResult:
        settings = self._settings
        t0 = time.perf_counter()

        model = self._ensure_model()
        yolo_loaded = model is not None
        scene_loaded = self._scene_clf.is_loaded()

        if not yolo_loaded and not scene_loaded:
            ms = (time.perf_counter() - t0) * 1000
            if settings.classify_demo_mode:
                return _demo_result_when_no_model(settings, ms)
            return _stub_empty(settings, ms)

        # Run YOLO and scene classifier in parallel when both are available.
        yolo_predictions: list[dict[str, Any]] = []
        coverage_ratio = 0.0
        mapped_pollution_boxes = 0
        raw_detector_boxes = 0
        max_mapped_confidence = 0.0
        scene_proba: dict[str, float] = {"WATER": 0.0, "SMOKE": 0.0}

        if yolo_loaded and scene_loaded:
            with ThreadPoolExecutor(max_workers=2) as pool:
                yolo_future = pool.submit(self._run_yolo, image_bytes)
                scene_future = pool.submit(self._scene_clf.predict_proba, image_bytes)
                for future in as_completed([yolo_future, scene_future]):
                    if future is yolo_future:
                        (
                            yolo_predictions,
                            coverage_ratio,
                            mapped_pollution_boxes,
                            raw_detector_boxes,
                            max_mapped_confidence,
                        ) = future.result()
                    else:
                        scene_proba = future.result()
        elif yolo_loaded:
            (
                yolo_predictions,
                coverage_ratio,
                mapped_pollution_boxes,
                raw_detector_boxes,
                max_mapped_confidence,
            ) = self._run_yolo(image_bytes)
        else:
            scene_proba = self._scene_clf.predict_proba(image_bytes)

        # Merge YOLO object results with scene classification.
        predictions = _merge_yolo_and_scene(
            yolo_predictions,
            scene_proba,
            settings.scene_classifier_threshold,
            raw_detector_boxes=raw_detector_boxes,
        )

        # Update coverage tracking: scene-only predictions get a synthetic coverage estimate.
        if not yolo_predictions and predictions:
            # Scene classifier fired without YOLO hits — use a mid-range placeholder.
            coverage_ratio = 0.10
            mapped_pollution_boxes = len(predictions)
            max_mapped_confidence = max(p["confidence"] for p in predictions)

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
        scene_scores_out = dict(scene_proba) if scene_loaded else None
        detector_ver = settings.model_version if yolo_loaded else None
        scene_ver = (
            (settings.scene_classifier_version.strip() or "loaded") if scene_loaded else None
        )

        return ClassificationResult(
            predictions=predictions,
            primary_class=primary_class,
            confidence=round(confidence, 4),
            action=action,
            inference_time_ms=round(ms, 2),
            model_version=_format_model_version(
                settings, yolo_loaded=yolo_loaded, scene_loaded=scene_loaded
            ),
            noise_supported=False,
            severity=severity,
            pollution_coverage_ratio=round(coverage_ratio, 6),
            image_relevance=image_relevance,
            yolo_active=yolo_loaded,
            scene_classifier_active=scene_loaded,
            detector_model_version=detector_ver,
            scene_model_version=scene_ver,
            scene_scores=scene_scores_out,
        )
