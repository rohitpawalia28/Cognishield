from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def load_rgb_image(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def pil_to_float_array(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0


def float_array_to_pil(array: np.ndarray) -> Image.Image:
    clipped = np.clip(array, 0.0, 1.0)
    return Image.fromarray((clipped * 255.0).round().astype(np.uint8), mode="RGB")


def resize_for_model(image: Image.Image, max_side: int = 512) -> Image.Image:
    width, height = image.size
    scale = min(max_side / max(width, height), 1.0)
    new_width = max(8, int(width * scale) // 8 * 8)
    new_height = max(8, int(height * scale) // 8 * 8)
    if (new_width, new_height) == image.size:
        return image
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

