"""Classify response exposes YOLO + scene audit fields."""

from io import BytesIO

from PIL import Image

from app.config import Settings
from app.core.pollution_classifier import PollutionClassifier, _format_model_version


def _tiny_jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color=(1, 2, 3)).save(buf, format="JPEG")
    return buf.getvalue()


def test_format_model_version_both_active():
    s = Settings(model_version="v-yolo", scene_classifier_version="v-scene")
    assert _format_model_version(s, yolo_loaded=True, scene_loaded=True) == "v-yolo|scene:v-scene"


def test_format_model_version_scene_off():
    s = Settings(model_version="v-yolo", scene_classifier_version="v-scene")
    assert _format_model_version(s, yolo_loaded=True, scene_loaded=False) == "v-yolo|scene:off"


def test_classify_stub_reports_inactive_stack():
    settings = Settings(
        model_path="ml/weights/__missing_yolo__.pt",
        scene_classifier_path="ml/weights/__missing_scene__.pt",
        model_version="v-yolo-test",
        scene_classifier_version="v-scene-test",
        classify_demo_mode=False,
    )
    out = PollutionClassifier(settings).classify_bytes(_tiny_jpeg_bytes())
    assert out.yolo_active is False
    assert out.scene_classifier_active is False
    assert out.scene_scores is None
    assert "scene:off" in out.model_version
