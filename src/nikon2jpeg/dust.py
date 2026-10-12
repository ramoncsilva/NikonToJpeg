"""Heuristic sensor-dust detection and inpainting."""

from __future__ import annotations

import cv2
import numpy as np

THRESHOLD = {"low": 18, "medium": 12, "high": 8}  # min luma drop vs. local background
DETECT_WIDTH = 2000  # detection runs at about this width
MAX_SPOT_FRAC = 0.004  # spot diameter limit, as a fraction of image width (NFR-4)
MAX_CONTRAST = 70  # darker than this is a real object, not dust
MAX_RING_STD = 14.0  # surroundings must be flat (sky, walls), not textured


def _odd(n: int) -> int:
    return n if n % 2 else n + 1


def detect(rgb: np.ndarray, sensitivity: str = "medium") -> np.ndarray:
    """Return a full-resolution uint8 mask (255 = dust) for the image."""
    h, w = rgb.shape[:2]
    scale = max(1, round(w / DETECT_WIDTH))
    small = rgb
    if scale != 1:
        small = cv2.resize(rgb, (w // scale, h // scale), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    sw = gray.shape[1]

    max_d = max(3, int(sw * MAX_SPOT_FRAC))
    background = cv2.medianBlur(gray, _odd(max(15, 3 * max_d)))
    residual = background.astype(np.int16) - gray.astype(np.int16)
    candidates = (residual >= THRESHOLD[sensitivity]).astype(np.uint8)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(candidates, connectivity=8)
    mask = np.zeros_like(gray)
    for i in range(1, n):
        x, y, bw, bh, area = (int(v) for v in stats[i])
        if area < 2 or bw > max_d or bh > max_d:
            continue
        if not 0.5 <= bw / bh <= 2.0 or area / (bw * bh) < 0.5:
            continue  # not roughly round
        blob = labels[y : y + bh, x : x + bw] == i
        if residual[y : y + bh, x : x + bw][blob].max() > MAX_CONTRAST:
            continue
        pad = max_d
        y0, y1 = max(0, y - pad), min(gray.shape[0], y + bh + pad)
        x0, x1 = max(0, x - pad), min(gray.shape[1], x + bw + pad)
        ring = labels[y0:y1, x0:x1] != i
        if gray[y0:y1, x0:x1][ring].std() > MAX_RING_STD:
            continue
        mask[y : y + bh, x : x + bw][blob] = 255

    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)
    if scale != 1:
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        mask = cv2.dilate(mask, np.ones((scale, scale), np.uint8))
    return mask


def remove_dust(rgb: np.ndarray, sensitivity: str = "medium") -> tuple[np.ndarray, np.ndarray]:
    """Return (cleaned image, mask)."""
    mask = detect(rgb, sensitivity)
    if not mask.any():
        return rgb, mask
    return cv2.inpaint(rgb, mask, 3, cv2.INPAINT_TELEA), mask
