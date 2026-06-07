"""Unit tests for HEIC detection helpers."""

from app.utils.image_decode import is_heic_upload


def test_is_heic_upload_by_extension() -> None:
    assert is_heic_upload("photo.HEIC", b"")
    assert is_heic_upload("x.heif", None)
    assert not is_heic_upload("photo.jpg", b"\xff\xd8\xff")


def test_is_heic_upload_by_ftyp_magic() -> None:
    # Minimal ftyp box header commonly seen in HEIF containers
    data = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00"
    assert is_heic_upload(None, data)
    assert not is_heic_upload("x.jpg", data[:8] + b"jpeg")
