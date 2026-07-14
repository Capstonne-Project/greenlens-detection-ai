"""Shared FastAPI dependencies."""

from functools import lru_cache

from app.core.image_compare import ImageCompareService
from app.core.pollution_classifier import PollutionClassifier


@lru_cache(maxsize=1)
def get_pollution_classifier_cached() -> PollutionClassifier:
    return PollutionClassifier()


@lru_cache(maxsize=1)
def get_image_compare_cached() -> ImageCompareService:
    return ImageCompareService()
