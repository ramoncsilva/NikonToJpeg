"""Edge-preserving noise reduction (chroma treated harder than luma)."""

from __future__ import annotations

import cv2
import numpy as np

# (luma strength, chroma strength) for fastNlMeansDenoisingColored
LEVELS = {"low": (2, 5), "medium": (4, 9), "high": (7, 14)}


def denoise(rgb: np.ndarray, level: str = "medium") -> np.ndarray:
    if level == "off":
        return rgb
    h_luma, h_color = LEVELS[level]
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    out = cv2.fastNlMeansDenoisingColored(bgr, None, h_luma, h_color, 7, 21)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
