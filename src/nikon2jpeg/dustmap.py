"""Learn sensor-dust positions that recur across a shoot.

Dust sits on the sensor, so it lands on the same pixels in every frame while the scene changes.
A spot found in many frames is almost surely dust and can be repaired in frames where the
per-image detector would have stayed cautious (textured backgrounds).
"""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from nikon2jpeg import decode, dust

MIN_IMAGES = 3  # below this a "recurring" spot proves nothing
MIN_FRACTION = 0.4  # fraction of frames a spot must appear in


def candidate(src: Path, sensitivity: str) -> tuple[int, np.ndarray] | None:
    """Per-frame dust candidates from the embedded preview, keyed by orientation."""
    try:
        got = decode.preview(src)
    except Exception:  # noqa: BLE001 - a bad file must not stop the learning pass
        return None
    if got is None:
        return None
    rgb, flip = got
    return flip, dust.detect_small(rgb, sensitivity)


def consensus(cands: list[tuple[int, np.ndarray]]) -> dict[int, np.ndarray]:
    """Combine per-frame masks into one map per orientation code."""
    groups: dict[int, list[np.ndarray]] = {}
    for flip, mask in cands:
        groups.setdefault(flip, []).append(mask)
    maps: dict[int, np.ndarray] = {}
    kernel = np.ones((3, 3), np.uint8)  # tolerate 1 px of registration slack
    for flip, masks in groups.items():
        if len(masks) < MIN_IMAGES:
            continue
        shape = masks[0].shape
        votes = np.zeros(shape, np.int16)
        for m in masks:
            if m.shape != shape:
                m = cv2.resize(m, shape[::-1], interpolation=cv2.INTER_NEAREST)
            votes += cv2.dilate(m, kernel) > 0
        need = max(2, math.ceil(MIN_FRACTION * len(masks)))
        found = (votes >= need).astype(np.uint8) * 255
        if found.any():
            maps[flip] = found
    return maps
