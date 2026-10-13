from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter

from .image_io import float_array_to_pil, pil_to_float_array


@dataclass(frozen=True)
class ProtectionConfig:
    epsilon: float = 8.0 / 255.0
    seed: int = 42
    iterations: int = 4
    compression_weight: float = 0.16
    jpeg_qualities: tuple[int, ...] = (95, 75)
    edge_weight: float = 0.65


def _jpeg_array_roundtrip(array: np.ndarray, quality: int) -> np.ndarray:
    image = float_array_to_pil(array)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)
    return pil_to_float_array(Image.open(buffer).convert("RGB"))


def _edge_mask(image_arr: np.ndarray, edge_weight: float) -> np.ndarray:
    gray = image_arr.mean(axis=2)
    grad_y = np.zeros_like(gray)
    grad_x = np.zeros_like(gray)
    grad_y[1:, :] = np.abs(gray[1:, :] - gray[:-1, :])
    grad_x[:, 1:] = np.abs(gray[:, 1:] - gray[:, :-1])
    edges = grad_x + grad_y
    if edges.max() > 0:
        edges = edges / edges.max()
    mask = (1.0 - edge_weight) + edge_weight * edges
    return mask[..., None].astype(np.float32)


def _high_frequency_noise(shape: tuple[int, int, int], seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(0.0, 1.0, size=shape).astype(np.float32)
    raw_image = Image.fromarray(((raw - raw.min()) / (raw.max() - raw.min() + 1e-8) * 255).astype(np.uint8))
    blurred = np.asarray(raw_image.filter(ImageFilter.GaussianBlur(radius=1.2)), dtype=np.float32)
    blurred = (blurred / 255.0) * 2.0 - 1.0
    high = raw - blurred
    high = high / (np.max(np.abs(high)) + 1e-8)
    return high.astype(np.float32)


def protect_image(image: Image.Image, config: ProtectionConfig) -> tuple[Image.Image, Image.Image]:
    """Create an imperceptible, compression-aware perturbation.

    This MVP uses high-frequency and edge-masked perturbations plus JPEG feedback. The
    target-model evaluation module measures whether the protected image disrupts SD-Turbo.
    """
    base = pil_to_float_array(image)
    noise = _high_frequency_noise(base.shape, config.seed)
    mask = _edge_mask(base, config.edge_weight)
    perturbation = np.clip(noise * mask * config.epsilon, -config.epsilon, config.epsilon)

    for _ in range(max(0, config.iterations)):
        candidate = np.clip(base + perturbation, 0.0, 1.0)
        feedback = np.zeros_like(candidate)
        for quality in config.jpeg_qualities:
            feedback += candidate - _jpeg_array_roundtrip(candidate, quality)
        feedback /= max(1, len(config.jpeg_qualities))
        perturbation = np.clip(
            perturbation + config.compression_weight * feedback,
            -config.epsilon,
            config.epsilon,
        )

    protected_arr = np.clip(base + perturbation, 0.0, 1.0)
    protected = float_array_to_pil(protected_arr)
    noise_preview = Image.fromarray(
        ((np.abs(perturbation) / max(config.epsilon, 1e-8)) * 255.0).clip(0, 255).astype(np.uint8),
        mode="RGB",
    )
    return protected, noise_preview

