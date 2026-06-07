"""Decode uploaded images (including HEIC/HEIF) to JPEG bytes for inference and preview."""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

_HEIC_SUFFIXES = {".heic", ".heif", ".hif"}

_HEIF_UNAVAILABLE_MSG = (
    "Server chưa đọc được HEIC (thiếu thư viện libheif). "
    "Dừng API, chạy: uv pip install --force-reinstall pillow-heif pillow "
    "rồi khởi động lại; hoặc export ảnh sang JPG trên điện thoại."
)


class HeifDecoderUnavailableError(RuntimeError):
    """Raised when pillow-heif / libheif cannot load on this host."""


def _ensure_windows_heif_dll_path() -> None:
    """Let Windows find libheif*.dll shipped next to site-packages."""
    if sys.platform != "win32":
        return
    import os
    import site

    for root in site.getsitepackages():
        if os.path.isdir(root):
            with contextlib.suppress(AttributeError, OSError):
                os.add_dll_directory(root)


def is_heic_upload(filename: str | None, data: bytes | None = None) -> bool:
    if filename and Path(filename).suffix.lower() in _HEIC_SUFFIXES:
        return True
    if data and len(data) >= 12:
        head = data[:32].lower()
        return b"ftyp" in head[4:8] and (
            b"heic" in head or b"heif" in head or b"mif1" in head or b"heix" in head
        )
    return False


def _register_heif_opener() -> None:
    _ensure_windows_heif_dll_path()
    try:
        import pillow_heif
    except ImportError as exc:
        raise HeifDecoderUnavailableError(_HEIF_UNAVAILABLE_MSG) from exc

    try:
        pillow_heif.register_heif_opener()
    except Exception as exc:
        raise HeifDecoderUnavailableError(_HEIF_UNAVAILABLE_MSG) from exc


def decode_image_bytes_to_jpeg(
    data: bytes,
    *,
    filename: str | None = None,
    quality: int = 90,
) -> tuple[bytes, str]:
    """Open image bytes with Pillow (+ HEIF plugin) and return JPEG."""
    if not data:
        raise ValueError("File ảnh rỗng.")

    if is_heic_upload(filename, data):
        _register_heif_opener()

    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as im:
            rgb = im.convert("RGB")
    except Exception as exc:
        hint = (
            " Định dạng HEIC này có thể là Live Photo hoặc variant không hỗ trợ — "
            "hãy Chia sẻ/Export sang JPG trên điện thoại rồi upload lại."
            if is_heic_upload(filename, data)
            else ""
        )
        raise ValueError(f"Không đọc được ảnh.{hint}") from exc

    out = io.BytesIO()
    rgb.save(out, format="JPEG", quality=quality, optimize=True)
    stem = Path(filename or "image").stem
    return out.getvalue(), f"{stem}.jpg"


def normalize_classify_image_bytes(data: bytes, filename: str | None = None) -> bytes:
    """Return bytes suitable for YOLO/Pillow classify (JPEG when input is HEIC)."""
    if is_heic_upload(filename, data):
        jpeg_bytes, _ = decode_image_bytes_to_jpeg(data, filename=filename)
        return jpeg_bytes
    return data
