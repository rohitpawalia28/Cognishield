from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cognishield.compression import evaluate_compression
from cognishield.config import MODEL_DIR, OUTPUT_DIR, ensure_project_dirs
from cognishield.image_io import load_rgb_image
from cognishield.metrics import ImageQualityMetrics, calculate_metrics
from cognishield.protector import ProtectionConfig, protect_image
from cognishield.sd_turbo import SDTurboTester


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate CogniShield quality, JPEG robustness, and optional SD-Turbo divergence."
    )
    parser.add_argument("--input-dir", type=Path, default=Path("data/input"))
    parser.add_argument("--run-name", type=str, default=None, help="Optional result-folder name.")
    parser.add_argument("--epsilon", type=float, default=8.0 / 255.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--qualities", type=int, nargs="+", default=[95, 75, 50])
    parser.add_argument("--prompt", default="a realistic photograph, natural lighting")
    parser.add_argument("--target-ssim-threshold", type=float, default=0.80)
    parser.add_argument("--quality-psnr-threshold", type=float, default=30.0)
    parser.add_argument("--quality-ssim-threshold", type=float, default=0.95)
    parser.add_argument("--jpeg-ssim-threshold", type=float, default=0.90)
    parser.add_argument("--skip-model", action="store_true", help="Run quality/JPEG evaluation without SD-Turbo.")
    parser.add_argument("--max-images", type=int, default=None, help="Limit images for a quick smoke test.")
    parser.add_argument("--example-count", type=int, default=12)
    return parser.parse_args()


def image_paths(input_dir: Path, max_images: int | None) -> list[Path]:
    paths = sorted(path for path in input_dir.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS)
    return paths[:max_images] if max_images else paths


def value_or_none(value: float | None) -> float | None:
    return None if value is None or not math.isfinite(float(value)) else round(float(value), 6)


def metrics_row(prefix: str, metrics: ImageQualityMetrics) -> dict[str, float | None]:
    return {
        f"{prefix}_psnr": value_or_none(metrics.psnr),
        f"{prefix}_ssim": value_or_none(metrics.ssim),
        f"{prefix}_mse": value_or_none(metrics.mse),
        f"{prefix}_mean_abs_delta": value_or_none(metrics.mean_abs_delta),
        f"{prefix}_max_abs_delta": value_or_none(metrics.max_abs_delta),
    }


def save_example(path: Path, images: list[Image.Image]) -> None:
    prepared = [image.convert("RGB").resize((256, 256), Image.Resampling.LANCZOS) for image in images]
    canvas = Image.new("RGB", (256 * len(prepared), 256), "#101827")
    for index, image in enumerate(prepared):
        canvas.paste(image, (index * 256, 0))
    canvas.save(path)


def mean_for(rows: list[dict[str, object]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return round(float(np.mean(values)), 6) if values else None


def percentage(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 2) if denominator else None


def write_charts(rows: list[dict[str, object]], summary: dict[str, object], output_dir: Path, qualities: list[int]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    quality_values = [row["quality_ssim"] for row in rows if row.get("quality_ssim") is not None]
    axes[0].hist(quality_values, bins=20, color="#247cff", edgecolor="white")
    axes[0].axvline(float(summary["criteria"]["quality_ssim_min"]), color="#22c985", linestyle="--", label="pass threshold")
    axes[0].set_title("Protected-image SSIM")
    axes[0].set_xlabel("SSIM")
    axes[0].set_ylabel("Images")
    axes[0].legend()

    jpeg_means = [mean_for(rows, f"jpeg_q{quality}_ssim") for quality in qualities]
    axes[1].bar([str(quality) for quality in qualities], [value or 0 for value in jpeg_means], color="#9c6cff")
    axes[1].axhline(float(summary["criteria"]["jpeg_ssim_min"]), color="#22c985", linestyle="--")
    axes[1].set_ylim(0, 1.05)
    axes[1].set_title("Mean JPEG robustness")
    axes[1].set_xlabel("JPEG quality")
    axes[1].set_ylabel("SSIM vs original")

    rates = summary["rates"]
    labels = ["Quality\npass", "JPEG\npass", "Target\ndivergence", "Combined\nsuccess"]
    values = [rates.get("quality_pass_rate"), rates.get("jpeg_pass_rate"), rates.get("target_divergence_rate"), rates.get("combined_success_rate")]
    bars = axes[2].bar(labels, [value or 0 for value in values], color=["#247cff", "#9c6cff", "#f3a943", "#22c985"])
    axes[2].set_ylim(0, 100)
    axes[2].set_title("Evaluation pass rates")
    axes[2].set_ylabel("Percent")
    for bar, value in zip(bars, values):
        axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, "N/A" if value is None else f"{value:.1f}%", ha="center", fontsize=9)

    fig.suptitle("CogniShield evaluation summary", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_dir / "evaluation_charts.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_report(summary: dict[str, object], output_dir: Path) -> None:
    rates = summary["rates"]
    averages = summary["averages"]
    criteria = summary["criteria"]
    report = f"""# CogniShield Evaluation Report

## Protocol

- Images processed: {summary['images_processed']}
- Images with SD-Turbo comparison: {summary['target_images_evaluated']}
- Epsilon: {summary['config']['epsilon']}
- Seed: {summary['config']['seed']}
- Compression-feedback steps: {summary['config']['iterations']}
- JPEG qualities: {', '.join(map(str, summary['config']['qualities']))}
- Target prompt: {summary['config']['prompt']}

## Predefined criteria

- Quality pass: PSNR ≥ {criteria['quality_psnr_min']} dB and SSIM ≥ {criteria['quality_ssim_min']}.
- JPEG pass: every selected JPEG variant has SSIM ≥ {criteria['jpeg_ssim_min']}.
- Target divergence: original-versus-protected SD-Turbo output SSIM ≤ {criteria['target_output_ssim_max']}.
- Combined success: quality pass and target divergence on the same image.

## Aggregate results

| Measure | Result |
| --- | ---: |
| Mean protected-image PSNR | {averages['quality_psnr']} dB |
| Mean protected-image SSIM | {averages['quality_ssim']} |
| Quality pass rate | {rates['quality_pass_rate']}% |
| JPEG pass rate | {rates['jpeg_pass_rate']}% |
| Target divergence rate | {rates['target_divergence_rate']}% |
| Combined success rate | {rates['combined_success_rate']}% |

## Interpretation

This report measures the selected protocol only. It does not establish universal protection against all image models or transformations. The target divergence rate is not a generic classifier accuracy; it is the proportion of evaluated images whose SD-Turbo outputs crossed the predefined divergence threshold while retaining the selected quality standard.
"""
    (output_dir / "report.md").write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()
    ensure_project_dirs()
    paths = image_paths(args.input_dir, args.max_images)
    if not paths:
        print(f"No supported images found in: {args.input_dir}")
        return 1
    if not args.skip_model and not MODEL_DIR.exists():
        print(f"SD-Turbo model directory not found: {MODEL_DIR}")
        print("Use --skip-model for a quality-only evaluation, or download the model first.")
        return 1

    run_name = args.run_name or datetime.now().strftime("evaluation_%Y%m%d_%H%M%S")
    output_dir = OUTPUT_DIR / "evaluations" / run_name
    output_dir.mkdir(parents=True, exist_ok=False)
    examples_dir = output_dir / "examples"
    examples_dir.mkdir()
    config = ProtectionConfig(epsilon=args.epsilon, seed=args.seed, iterations=args.iterations, jpeg_qualities=tuple(args.qualities))
    tester = None if args.skip_model else SDTurboTester(MODEL_DIR)
    rows: list[dict[str, object]] = []
    example_indexes = set(np.linspace(0, len(paths) - 1, num=min(args.example_count, len(paths)), dtype=int).tolist())

    print(f"Starting evaluation: {len(paths)} images")
    for index, image_path in enumerate(paths, start=1):
        row: dict[str, object] = {"image": str(image_path), "filename": image_path.name, "status": "ok"}
        try:
            original = load_rgb_image(image_path)
            protected, _noise = protect_image(original, config)
            quality = calculate_metrics(original, protected)
            row.update(metrics_row("quality", quality))
            quality_ssim = quality.ssim if quality.ssim is not None else 0.0
            quality_pass = quality.psnr >= args.quality_psnr_threshold and quality_ssim >= args.quality_ssim_threshold
            row["quality_pass"] = quality_pass

            compression = evaluate_compression(original, protected, args.qualities)
            jpeg_pass = True
            for jpeg_quality, jpeg_metrics in compression.items():
                row.update(metrics_row(f"jpeg_q{jpeg_quality}", jpeg_metrics))
                jpeg_ssim = jpeg_metrics.ssim if jpeg_metrics.ssim is not None else 0.0
                jpeg_pass = jpeg_pass and jpeg_ssim >= args.jpeg_ssim_threshold
            row["jpeg_pass"] = jpeg_pass

            target_success = None
            original_target = protected_target = None
            if tester is not None:
                original_target = tester.run(original, prompt=args.prompt, seed=args.seed).image
                protected_target = tester.run(protected, prompt=args.prompt, seed=args.seed).image
                target_metrics = calculate_metrics(original_target, protected_target)
                row.update(metrics_row("target_output", target_metrics))
                target_ssim = target_metrics.ssim if target_metrics.ssim is not None else 1.0
                target_success = target_ssim <= args.target_ssim_threshold
                row["target_divergence_pass"] = target_success
                row["combined_success"] = bool(quality_pass and target_success)
            else:
                row["target_divergence_pass"] = None
                row["combined_success"] = None

            if index - 1 in example_indexes and original_target is not None and protected_target is not None:
                save_example(examples_dir / f"{index:03d}_{image_path.stem}.png", [original, protected, original_target, protected_target])
        except Exception as exc:
            row.update({"status": "error", "error": str(exc), "quality_pass": False, "jpeg_pass": False, "target_divergence_pass": None, "combined_success": None})
        rows.append(row)
        print(f"[{index}/{len(paths)}] {image_path.name}: {row['status']}")

    completed = [row for row in rows if row["status"] == "ok"]
    target_rows = [row for row in completed if row.get("target_divergence_pass") is not None]
    quality_passes = sum(bool(row.get("quality_pass")) for row in completed)
    jpeg_passes = sum(bool(row.get("jpeg_pass")) for row in completed)
    target_passes = sum(bool(row.get("target_divergence_pass")) for row in target_rows)
    combined_passes = sum(bool(row.get("combined_success")) for row in target_rows)
    summary: dict[str, object] = {
        "run_name": run_name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "images_requested": len(paths),
        "images_processed": len(completed),
        "images_failed": len(rows) - len(completed),
        "target_images_evaluated": len(target_rows),
        "config": {"epsilon": args.epsilon, "epsilon_pixels": round(args.epsilon * 255, 3), "seed": args.seed, "iterations": args.iterations, "qualities": args.qualities, "prompt": args.prompt, "skip_model": args.skip_model},
        "criteria": {"quality_psnr_min": args.quality_psnr_threshold, "quality_ssim_min": args.quality_ssim_threshold, "jpeg_ssim_min": args.jpeg_ssim_threshold, "target_output_ssim_max": args.target_ssim_threshold},
        "averages": {"quality_psnr": mean_for(completed, "quality_psnr"), "quality_ssim": mean_for(completed, "quality_ssim"), "quality_mse": mean_for(completed, "quality_mse"), "target_output_ssim": mean_for(target_rows, "target_output_ssim"), "target_output_psnr": mean_for(target_rows, "target_output_psnr")},
        "rates": {"quality_pass_rate": percentage(quality_passes, len(completed)), "jpeg_pass_rate": percentage(jpeg_passes, len(completed)), "target_divergence_rate": percentage(target_passes, len(target_rows)), "combined_success_rate": percentage(combined_passes, len(target_rows))},
    }

    fields = sorted({field for row in rows for field in row})
    with (output_dir / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_charts(completed, summary, output_dir, args.qualities)
    write_report(summary, output_dir)

    print("\nEvaluation complete")
    print(json.dumps(summary["rates"], indent=2))
    print(f"Results: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
