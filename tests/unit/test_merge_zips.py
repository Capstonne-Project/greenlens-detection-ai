"""Merge pollution YOLO ZIPs (TRASH/WATER) into one dataset."""

import io
import zipfile

import pytest

from app.core.training_jobs import merge_zips_direct


def _zip_yolo(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, data in entries.items():
            zf.writestr(path, data)
    return buf.getvalue()


def _tiny_png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_merge_many_water_zips():
    png = _tiny_png()
    label = b"1 0.5 0.5 0.2 0.2\n"
    zip_a = _zip_yolo({"images/train/a.png": png, "labels/train/a.txt": label})
    zip_b = _zip_yolo({"images/train/b.png": png, "labels/train/b.txt": label})
    zip_c = _zip_yolo({"images/train/c.png": png, "labels/train/c.txt": label})

    merged_bytes, stats = merge_zips_direct(
        [(zip_a, "WATER"), (zip_b, "WATER"), (zip_c, "WATER")],
        seed=42,
    )

    assert stats["total_images"] == 3
    assert stats["class_counts"]["1"] == 3
    assert len(stats["slots"]) == 3

    with zipfile.ZipFile(io.BytesIO(merged_bytes)) as zf:
        names = zf.namelist()
        assert any(n.startswith("images/train/") for n in names)
        assert any(n.startswith("images/test/") for n in names)
        assert "data.yaml" in names
        yaml_text = zf.read("data.yaml").decode()
        assert "nc: 2" in yaml_text
        assert "WATER" in yaml_text


def test_merge_mixed_trash_and_water():
    png = _tiny_png()
    trash_zip = _zip_yolo({"images/train/t.png": png, "labels/train/t.txt": b"0 0.5 0.5 0.3 0.3\n"})
    water_zip = _zip_yolo({"images/train/w.png": png, "labels/train/w.txt": b"1 0.5 0.5 0.3 0.3\n"})

    _, stats = merge_zips_direct([(trash_zip, "TRASH"), (water_zip, "WATER")])

    assert stats["total_images"] == 2
    assert stats["class_counts"]["0"] == 1
    assert stats["class_counts"]["1"] == 1


def test_merge_requires_images():
    empty = _zip_yolo({})
    with pytest.raises(ValueError, match="Không tìm thấy ảnh"):
        merge_zips_direct([(empty, "WATER")])
