"""classify_demo_mode when weights file is missing."""

from io import BytesIO

from PIL import Image

from app.config import Settings
from app.core.pollution_classifier import PollutionClassifier


def _tiny_jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color=(1, 2, 3)).save(buf, format="JPEG")
    return buf.getvalue()


def test_demo_mode_returns_suggest_stub():
    settings = Settings(
        model_path="ml/weights/__surely_missing_file__.pt",
        model_version="v0.test",
        classify_demo_mode=True,
    )
    clf = PollutionClassifier(settings)
    assert clf.model_is_loaded() is False
    out = clf.classify_bytes(_tiny_jpeg_bytes())
    assert out.action == "SUGGEST"
    assert out.primary_class == "TRASH"
    assert out.predictions and out.predictions[0]["class"] == "TRASH"
    assert "demo-no-weights" in out.model_version
    assert out.severity == "MEDIUM"
    assert out.pollution_coverage_ratio >= 0.0
    assert out.image_relevance == "POLLUTION_LIKELY"


def test_without_demo_mode_stays_empty_stub():
    settings = Settings(
        model_path="ml/weights/__surely_missing_file__.pt",
        model_version="v0.test",
        classify_demo_mode=False,
    )
    clf = PollutionClassifier(settings)
    out = clf.classify_bytes(_tiny_jpeg_bytes())
    assert out.action == "KEEP_USER_CHOICE"
    assert out.primary_class is None
    assert out.predictions == []
    assert out.severity == "LOW"
    assert out.pollution_coverage_ratio == 0.0
    assert out.image_relevance == "NOT_POLLUTION_OR_UNRELATED"
