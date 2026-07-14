"""Unit tests for DINOv2 cosine similarity + threshold logic (no weights download)."""

import torch

from app.core.image_compare import ImageCompareService


def _make_service(monkeypatch, vectors: dict[bytes, list[float]]) -> ImageCompareService:
    """Build a service whose _embed returns fixed, L2-normalized vectors per input bytes."""
    svc = ImageCompareService()

    def fake_embed(image_bytes: bytes):
        vec = torch.tensor([vectors[image_bytes]], dtype=torch.float32)
        return torch.nn.functional.normalize(vec, dim=-1)

    monkeypatch.setattr(svc, "_embed", fake_embed)
    return svc


def test_identical_embeddings_same_scene(monkeypatch):
    svc = _make_service(monkeypatch, {b"a": [1.0, 2.0, 3.0], b"b": [1.0, 2.0, 3.0]})
    result = svc.compare_bytes(b"a", b"b")
    assert result.confidence > 0.99
    assert result.is_same_scene is True
    assert result.model == "dinov2-base"


def test_orthogonal_embeddings_not_same_scene(monkeypatch):
    svc = _make_service(monkeypatch, {b"a": [1.0, 0.0], b"b": [0.0, 1.0]})
    result = svc.compare_bytes(b"a", b"b")
    assert result.confidence < 0.5
    assert result.is_same_scene is False


def test_threshold_boundary(monkeypatch):
    svc = _make_service(monkeypatch, {b"a": [1.0, 0.0], b"b": [1.0, 0.0]})
    svc._settings.compare_threshold = 0.95
    result = svc.compare_bytes(b"a", b"b")
    assert result.is_same_scene is True
