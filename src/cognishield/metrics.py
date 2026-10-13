from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from PIL import Image

from .image_io import pil_to_float_array


@dataclass(frozen=True)
class ImageQualityMetrics:
    psnr: float
    ssim: float | None
    mse: float
    mean_abs_delta: float
    max_abs_delta: float

    def to_dict(self) -> dict[str, float | None]:
        return asdict(self)


def calculate_metrics(original: Image.Image, protected: Image.Image) -> ImageQualityMetrics:
    if original.size != protected.size:
        protected = protected.resize(original.size, Image.Resampling.LANCZOS)

    original_arr = pil_to_float_array(original)
    protected_arr = pil_to_float_array(protected)
    diff = original_arr - protected_arr
    mse = float(np.mean(diff**2))
    psnr = float("inf") if mse == 0 else float(20.0 * math.log10(1.0 / math.sqrt(mse)))

    ssim_value: float | None
    try:
        from skimage.metrics import structural_similarity

        ssim_value = float(
            structural_similarity(original_arr, protected_arr, channel_axis=2, data_range=1.0)
        )
    except Exception:
        ssim_value = None

    return ImageQualityMetrics(
        psnr=psnr,
        ssim=ssim_value,
        mse=mse,
        mean_abs_delta=float(np.mean(np.abs(diff))),
        max_abs_delta=float(np.max(np.abs(diff))),
    )


def make_difference_image(original: Image.Image, protected: Image.Image, gain: float = 12.0) -> Image.Image:
    if original.size != protected.size:
        protected = protected.resize(original.size, Image.Resampling.LANCZOS)
    original_arr = pil_to_float_array(original)
    protected_arr = pil_to_float_array(protected)
    diff = np.abs(protected_arr - original_arr) * gain
    return Image.fromarray((np.clip(diff, 0.0, 1.0) * 255.0).astype(np.uint8), mode="RGB")

