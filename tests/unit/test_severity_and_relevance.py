"""Unit tests for severity + image relevance helpers."""

from app.config import Settings
from app.core.report_image_relevance import classify_image_relevance
from app.core.severity_estimator import severity_from_pollution_coverage


def test_severity_bands_defaults():
    s = Settings()
    assert (
        severity_from_pollution_coverage(
            0.01,
            thr_low=s.severity_cover_low_below,
            thr_med=s.severity_cover_medium_below,
            thr_high=s.severity_cover_high_below,
        )
        == "LOW"
    )
    assert (
        severity_from_pollution_coverage(
            0.10,
            thr_low=s.severity_cover_low_below,
            thr_med=s.severity_cover_medium_below,
            thr_high=s.severity_cover_high_below,
        )
        == "MEDIUM"
    )
    assert (
        severity_from_pollution_coverage(
            0.55,
            thr_low=s.severity_cover_low_below,
            thr_med=s.severity_cover_medium_below,
            thr_high=s.severity_cover_high_below,
        )
        == "CRITICAL"
    )


def test_relevance_no_boxes():
    assert (
        classify_image_relevance(
            mapped_pollution_boxes=0,
            raw_detector_boxes=0,
            max_mapped_confidence=0.0,
            relevance_min_confidence=0.3,
        )
        == "NOT_POLLUTION_OR_UNRELATED"
    )


def test_relevance_unclear_mapped_raw():
    assert (
        classify_image_relevance(
            mapped_pollution_boxes=0,
            raw_detector_boxes=3,
            max_mapped_confidence=0.0,
            relevance_min_confidence=0.3,
        )
        == "UNCLEAR_NEED_MANUAL_REVIEW"
    )


def test_relevance_pollution_likely():
    assert (
        classify_image_relevance(
            mapped_pollution_boxes=2,
            raw_detector_boxes=2,
            max_mapped_confidence=0.8,
            relevance_min_confidence=0.3,
        )
        == "POLLUTION_LIKELY"
    )


def test_relevance_weak_conf_mapped():
    assert (
        classify_image_relevance(
            mapped_pollution_boxes=1,
            raw_detector_boxes=1,
            max_mapped_confidence=0.1,
            relevance_min_confidence=0.3,
        )
        == "UNCLEAR_NEED_MANUAL_REVIEW"
    )
