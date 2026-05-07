"""Integration coverage for classify-only AI service scope."""

from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app


def _minimal_jpeg() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (32, 32), (128, 64, 32)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(name="tiny_jpeg_tmp")
def _tiny_jpeg_tmp(tmp_path: Path):
    jpeg = _minimal_jpeg()
    p = tmp_path / "tiny.jpg"
    p.write_bytes(jpeg)
    return p, jpeg


@pytest.mark.asyncio
async def test_classify_returns_expected_shape_without_weights(tiny_jpeg_tmp):
    path, _ = tiny_jpeg_tmp
    uri = path.as_uri()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/classify", json={"image_url": uri})

    assert resp.status_code == 200
    data = resp.json()
    assert "model_version" in data
    assert data["noise_supported"] is False
    assert data["action"] == "KEEP_USER_CHOICE"
    assert data["predictions"] == []
    assert data["severity"] == "LOW"
    assert data["image_relevance"] == "NOT_POLLUTION_OR_UNRELATED"
    assert data["pollution_coverage_ratio"] == 0.0


@pytest.mark.asyncio
async def test_classify_upload_multipart_response_shape():
    jpeg = _minimal_jpeg()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/classify-upload",
            files={"image": ("upload.jpg", jpeg, "image/jpeg")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_version"]
    assert "action" in data
    assert "severity" in data
    assert "image_relevance" in data


@pytest.mark.asyncio
async def test_demo_static_file_available():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/demo/demo_capture_classify.html")
    assert resp.status_code == 200
    assert "classify-upload" in resp.text
    assert "severity" in resp.text
