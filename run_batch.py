from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cognishield.compression import evaluate_compression, save_jpeg_variants
from cognishield.config import KEY_DIR, OUTPUT_DIR, ensure_project_dirs
from cognishield.image_io import load_rgb_image
from cognishield.metrics import calculate_metrics, make_difference_image
from cognishield.protector import ProtectionConfig, protect_image
from cognishield.provenance import sign_image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def iter_images(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CogniShield over a folder of images")
    parser.add_argument("--input-dir", type=Path, default=Path("data/input"))
    parser.add_argument("--epsilon", type=float, default=8.0 / 255.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--qualities", type=int, nargs="+", default=[95, 75, 50])
    args = parser.parse_args()

    ensure_project_dirs()
    image_paths = iter_images(args.input_dir)
    if not image_paths:
        print(f"No images found in {args.input_dir}")
        return 1

    batch_dir = OUTPUT_DIR / "batch"
    batch_dir.mkdir(parents=True, exist_ok=True)
    csv_path = batch_dir / "summary.csv"
    config = ProtectionConfig(
        epsilon=args.epsilon,
        seed=args.seed,
        iterations=args.iterations,
        jpeg_qualities=tuple(args.qualities),
    )

    rows: list[dict[str, str | float | int | None]] = []
    for image_path in image_paths:
        original = load_rgb_image(image_path)
        protected, noise_preview = protect_image(original, config)
        run_dir = batch_dir / image_path.stem
        run_dir.mkdir(parents=True, exist_ok=True)

        protected_path = run_dir / "protected.png"
        protected.save(protected_path)
        noise_preview.save(run_dir / "noise_preview.png")
        make_difference_image(original, protected).save(run_dir / "difference_x12.png")
        save_jpeg_variants(protected, run_dir, args.qualities)
        sign_image(protected_path, KEY_DIR, metadata={"source": str(image_path)})

        metrics = calculate_metrics(original, protected)
        row: dict[str, str | float | int | None] = {
            "image": str(image_path),
            "width": original.width,
            "height": original.height,
            "psnr": metrics.psnr,
            "ssim": metrics.ssim,
            "mse": metrics.mse,
            "mean_abs_delta": metrics.mean_abs_delta,
            "max_abs_delta": metrics.max_abs_delta,
        }
        for quality, compressed_metrics in evaluate_compression(original, protected, args.qualities).items():
            row[f"jpeg_{quality}_psnr"] = compressed_metrics.psnr
            row[f"jpeg_{quality}_ssim"] = compressed_metrics.ssim
        rows.append(row)
        print(f"Processed {image_path}")

    fieldnames = sorted({key for row in rows for key in row})
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

