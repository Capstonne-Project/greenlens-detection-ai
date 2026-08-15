"""Integration coverage for POST /api/v1/compare-images (DINOv2 Tier 2)."""

from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.api.v1 import compare
from app.core.image_compare import CompareResult
from app.main import app


def _minimal_jpeg(color: tuple[int, int, int]) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (32, 32), color).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(name="two_jpegs")
def _two_jpegs(tmp_path: Path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    a.write_bytes(_minimal_jpeg((128, 64, 32)))
    b.write_bytes(_minimal_jpeg((32, 64, 128)))
    return a, b


class _FakeCompare:
    """Stub embedder — avoids downloading DINOv2 weights in tests."""

    def __init__(self, *, loaded: bool = True, confidence: float = 0.87) -> None:
        self._loaded = loaded
        self._confidence = confidence

    def model_is_loaded(self) -> bool:
        return self._loaded

    def compare_bytes(self, a: bytes, b: bytes) -> CompareResult:
        return CompareResult(
            confidence=self._confidence,
            is_same_scene=self._confidence >= 0.80,
            model="dinov2-base",
        )


@pytest.mark.asyncio
async def test_compare_images_happy_path(monkeypatch, two_jpegs):
    a, b = two_jpegs
    monkeypatch.setattr(compare, "get_image_compare_cached", lambda: _FakeCompare())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/compare-images",
            json={"image_url_a": a.as_uri(), "image_url_b": b.as_uri()},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["confidence"] == 0.87
    assert data["is_same_scene"] is True
    assert data["model"] == "dinov2-base"
    assert data["processing_time_ms"] >= 0


@pytest.mark.asyncio
async def test_compare_images_model_unavailable_returns_503(monkeypatch, two_jpegs):
    a, b = two_jpegs
    monkeypatch.setattr(
        compare, "get_image_compare_cached", lambda: _FakeCompare(loaded=False)
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/compare-images",
            json={"image_url_a": a.as_uri(), "image_url_b": b.as_uri()},
        )

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_compare_images_bad_url_returns_400(monkeypatch, two_jpegs):
    a, _ = two_jpegs
    monkeypatch.setattr(compare, "get_image_compare_cached", lambda: _FakeCompare())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/compare-images",
            json={
                "image_url_a": a.as_uri(),
                "image_url_b": "file:///nonexistent/does_not_exist.jpg",
            },
        )

    assert resp.status_code == 400
    assert "image_url_b" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_compare_images_upload_happy_path(monkeypatch, two_jpegs):
    a_bytes = _minimal_jpeg((128, 64, 32))
    b_bytes = _minimal_jpeg((32, 64, 128))
    monkeypatch.setattr(compare, "get_image_compare_cached", lambda: _FakeCompare())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/compare-images-upload",
            files={
                "image_a": ("a.jpg", a_bytes, "image/jpeg"),
                "image_b": ("b.jpg", b_bytes, "image/jpeg"),
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["confidence"] == 0.87
    assert data["is_same_scene"] is True
    assert data["model"] == "dinov2-base"


@pytest.mark.asyncio
async def test_compare_images_upload_empty_file_returns_400(monkeypatch):
    monkeypatch.setattr(compare, "get_image_compare_cached", lambda: _FakeCompare())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/compare-images-upload",
            files={
                "image_a": ("a.jpg", b"", "image/jpeg"),
                "image_b": ("b.jpg", _minimal_jpeg((1, 2, 3)), "image/jpeg"),
            },
        )

    assert resp.status_code == 400
    assert "image_a" in resp.json()["detail"]
