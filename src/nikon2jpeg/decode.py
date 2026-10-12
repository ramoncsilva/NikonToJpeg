"""NEF decoding via LibRaw (rawpy), with embedded-preview fast path."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image, ImageOps


@dataclass
class Decoded:
    rgb: np.ndarray  # HxWx3 uint8, sRGB, already upright
    exif: bytes | None  # raw EXIF segment from the embedded preview, if any
    flip: int = 0  # LibRaw orientation code; same code = same sensor-to-image mapping


def _thumb(raw: rawpy.RawPy):
    try:
        return raw.extract_thumb()
    except (rawpy.LibRawNoThumbnailError, rawpy.LibRawUnsupportedThumbnailError):
        return None


def _exif_from_thumb(thumb) -> bytes | None:
    if thumb is None or thumb.format != rawpy.ThumbFormat.JPEG:
        return None
    with Image.open(io.BytesIO(thumb.data)) as im:
        return im.info.get("exif")


def _preview_rgb(thumb) -> np.ndarray:
    if thumb.format == rawpy.ThumbFormat.JPEG:
        with Image.open(io.BytesIO(thumb.data)) as im:
            return np.asarray(ImageOps.exif_transpose(im).convert("RGB"))
    return np.asarray(thumb.data)


def preview(path: Path) -> tuple[np.ndarray, int] | None:
    """Upright embedded preview and orientation code (cheap; used to learn the dust map)."""
    with rawpy.imread(str(path)) as raw:
        thumb = _thumb(raw)
        return None if thumb is None else (_preview_rgb(thumb), raw.sizes.flip)


def decode(path: Path, target_edge: int | None, fast: bool = False) -> Decoded:
    with rawpy.imread(str(path)) as raw:
        thumb = _thumb(raw)
        exif = _exif_from_thumb(thumb)
        if fast and thumb is not None:
            return Decoded(_preview_rgb(thumb), exif, raw.sizes.flip)
        try:
            long_edge = max(raw.sizes.iwidth, raw.sizes.iheight)
            # Skipping demosaic interpolation is a big win when we downscale anyway.
            half = target_edge is not None and long_edge // 2 >= target_edge
            rgb = raw.postprocess(
                use_camera_wb=True,
                output_bps=8,
                output_color=rawpy.ColorSpace.sRGB,
                half_size=half,
            )
        except Exception:
            if thumb is None:
                raise
            return Decoded(_preview_rgb(thumb), exif, raw.sizes.flip)  # fall back to the preview
        return Decoded(rgb, exif, raw.sizes.flip)
