"""Resize, sharpen and write the JPEG (sRGB ICC, filtered EXIF) atomically."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import piexif
from PIL import Image, ImageCms

_SRGB_ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def resize(rgb: np.ndarray, max_edge: int | None) -> np.ndarray:
    if max_edge is None:
        return rgb
    h, w = rgb.shape[:2]
    scale = max_edge / max(h, w)
    if scale >= 1:  # never upscale
        return rgb
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    return cv2.resize(rgb, size, interpolation=cv2.INTER_AREA)


def sharpen(rgb: np.ndarray, amount: float = 0.4, sigma: float = 0.8) -> np.ndarray:
    blurred = cv2.GaussianBlur(rgb, (0, 0), sigma)
    return cv2.addWeighted(rgb, 1 + amount, blurred, -amount, 0)


def filter_exif(exif: bytes | None, keep_gps: bool) -> bytes | None:
    """Reset orientation (pixels are already upright), drop thumbnail and GPS."""
    if not exif:
        return None
    try:
        data = piexif.load(exif)
        data["0th"][piexif.ImageIFD.Orientation] = 1
        data["thumbnail"] = None
        data["1st"] = {}
        if not keep_gps:
            data["GPS"] = {}
        return piexif.dump(data)
    except Exception:  # noqa: BLE001
        return None


def write_jpeg(rgb: np.ndarray, dst: Path, quality: int, exif: bytes | None) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    try:
        Image.fromarray(rgb).save(
            tmp,
            format="JPEG",
            quality=quality,
            progressive=True,
            optimize=True,
            subsampling="4:2:0",
            icc_profile=_SRGB_ICC,
            **({"exif": exif} if exif else {}),
        )
        os.replace(tmp, dst)
    finally:
        tmp.unlink(missing_ok=True)
