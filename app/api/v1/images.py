"""Image utilities for demo upload (HEIC → JPEG preview)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from app.utils.image_decode import HeifDecoderUnavailableError, decode_image_bytes_to_jpeg

router = APIRouter(prefix="/images", tags=["images"])

_MAX_BYTES = 20 * 1024 * 1024


@router.post("/normalize")
async def normalize_image_for_preview(
    image: Annotated[
        UploadFile,
        File(description="HEIC/HEIF/JPEG/PNG — trả về JPEG để xem trước trên trình duyệt."),
    ],
) -> Response:
    """Convert uploaded image to JPEG (fixes HEIC preview on Chrome/Windows)."""
    payload = await image.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(payload) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image too large.")

    try:
        jpeg_bytes, out_name = decode_image_bytes_to_jpeg(payload, filename=image.filename)
    except HeifDecoderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xử lý ảnh: {type(exc).__name__}",
        ) from exc

    return Response(
        content=jpeg_bytes,
        media_type="image/jpeg",
        headers={"Content-Disposition": f'inline; filename="{out_name}"'},
    )
