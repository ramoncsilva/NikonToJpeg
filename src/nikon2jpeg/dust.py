"""Heuristic sensor-dust detection and inpainting."""

from __future__ import annotations

import cv2
import numpy as np

THRESHOLD = {"low": 18, "medium": 12, "high": 8}  # min luma drop vs. local background
DETECT_WIDTH = 2000  # detection runs at about this width
MAX_SPOT_FRAC = 0.004  # spot diameter limit, as a fraction of image width (NFR-4)
MAX_CONTRAST = 70  # darker than this is a real object, not dust
MAX_RING_STD = 14.0  # surroundings must be flat (sky, walls), not textured
NOISE_K = 3.0  # spot must stand out by this many local noise/texture deviations
MIN_BACKGROUND = 40  # dust is invisible in near-black areas; they are only noisy
MAX_COVERAGE = 0.005  # real dust is sparse; more masked area means we are picking up noise


def _odd(n: int) -> int:
    return n if n % 2 else n + 1


def detect_small(rgb: np.ndarray, sensitivity: str = "medium") -> np.ndarray:
    """Return a uint8 mask (255 = dust) on the detection grid (about DETECT_WIDTH wide)."""
    h, w = rgb.shape[:2]
    scale = max(1, round(w / DETECT_WIDTH))
    small = rgb
    if scale != 1:
        small = cv2.resize(rgb, (w // scale, h // scale), interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY), (0, 0), 0.8)
    sw = gray.shape[1]

    max_d = max(3, int(sw * MAX_SPOT_FRAC))
    background = cv2.medianBlur(gray, _odd(max(15, 3 * max_d)))
    residual = background.astype(np.int16) - gray.astype(np.int16)
    # Local deviation of the residual: high in noisy or textured regions, low on clean flat ones.
    local_sigma = cv2.blur(np.abs(residual).astype(np.float32), (_odd(4 * max_d),) * 2)
    threshold = THRESHOLD[sensitivity] + NOISE_K * local_sigma
    candidates = ((residual >= threshold) & (background >= MIN_BACKGROUND)).astype(np.uint8)

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

    if (mask > 0).mean() > MAX_COVERAGE:
        mask[:] = 0  # detector is fooled by noise; touching nothing is safer than smearing
    return mask


def expand(small_mask: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Grow a detection-grid mask a little and scale it to full resolution (h, w)."""
    h, w = shape
    mask = cv2.dilate(small_mask, np.ones((3, 3), np.uint8), iterations=2)
    if mask.shape != (h, w):
        scale = max(1, round(w / mask.shape[1]))
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        mask = cv2.dilate(mask, np.ones((scale, scale), np.uint8))
    return mask


def detect(
    rgb: np.ndarray, sensitivity: str = "medium", shoot_map: np.ndarray | None = None
) -> np.ndarray:
    """Full-resolution dust mask; optionally merged with a recurring-spot map for the shoot."""
    small = detect_small(rgb, sensitivity)
    if shoot_map is not None:
        extra = shoot_map
        if extra.shape != small.shape:
            extra = cv2.resize(extra, small.shape[::-1], interpolation=cv2.INTER_NEAREST)
        small = cv2.bitwise_or(small, extra)
    return expand(small, rgb.shape[:2])


def remove_dust(
    rgb: np.ndarray, sensitivity: str = "medium", shoot_map: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Return (cleaned image, mask)."""
    mask = detect(rgb, sensitivity, shoot_map)
    if not mask.any():
        return rgb, mask
    return cv2.inpaint(rgb, mask, 3, cv2.INPAINT_TELEA), mask
