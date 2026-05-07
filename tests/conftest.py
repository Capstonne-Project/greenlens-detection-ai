"""Pytest fixtures shared across tests."""

import pytest


@pytest.fixture(autouse=True)
def clear_pollution_classifier_cache():
    from app.api import deps

    deps.get_pollution_classifier_cached.cache_clear()
    yield
    deps.get_pollution_classifier_cached.cache_clear()
