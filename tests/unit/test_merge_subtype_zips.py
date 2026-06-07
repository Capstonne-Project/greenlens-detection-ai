"""Merge trash subtype ZIPs into ImageFolder train/val layout."""

import io
import json
import zipfile

import pytest

from app.core.training_jobs import merge_subtype_zips_direct


def _zip_with_images(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, data in entries.items():
            zf.writestr(path, data)
    return buf.getvalue()


def _tiny_png() -> bytes:
    # minimal valid 1x1 PNG
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_merge_subtype_zips_train_val_split():
    png = _tiny_png()
    zip_a = _zip_with_images({"plastic/a1.png": png, "plastic/a2.png": png})
    zip_b = _zip_with_images({"mask/m1.png": png})

    merged_bytes, stats = merge_subtype_zips_direct(
        [(zip_a, "RECYCLABLE"), (zip_b, "MEDICAL")],
        val_fraction=0.15,
        seed=42,
    )

    assert stats["total_train"] + stats["total_val"] == 3
    assert stats["train_class_counts"]["RECYCLABLE"] >= 1
    assert stats["train_class_counts"]["MEDICAL"] >= 1

    with zipfile.ZipFile(io.BytesIO(merged_bytes)) as zf:
        names = zf.namelist()
        assert any(n.startswith("images/train/RECYCLABLE/") for n in names)
        assert any(n.startswith("images/val/") for n in names)
        info = json.loads(zf.read("dataset_info.json"))
        assert info["format"] == "trash_subtype_imagefolder"


def test_merge_subtype_requires_images():
    empty = _zip_with_images({"readme.txt": b"no images"})
    with pytest.raises(ValueError, match="Không tìm thấy ảnh"):
        merge_subtype_zips_direct([(empty, "ORGANIC")])
