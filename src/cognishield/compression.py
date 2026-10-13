from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

from .metrics import ImageQualityMetrics, calculate_metrics


def jpeg_roundtrip(image: Image.Image, quality: int) -> Image.Image:
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def save_jpeg_variants(image: Image.Image, output_dir: Path, qualities: list[int]) -> dict[int, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[int, Path] = {}
    for quality in qualities:
        path = output_dir / f"protected_jpeg_q{quality}.jpg"
        image.convert("RGB").save(path, format="JPEG", quality=quality, optimize=True)
        paths[quality] = path
    return paths


def evaluate_compression(
    original: Image.Image, protected: Image.Image, qualities: list[int]
) -> dict[int, ImageQualityMetrics]:
    results: dict[int, ImageQualityMetrics] = {}
    for quality in qualities:
        compressed = jpeg_roundtrip(protected, quality)
        results[quality] = calculate_metrics(original, compressed)
    return results

