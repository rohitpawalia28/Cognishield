from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cognishield.compression import evaluate_compression, save_jpeg_variants
from cognishield.config import KEY_DIR, OUTPUT_DIR, ensure_project_dirs
from cognishield.image_io import load_rgb_image
from cognishield.metrics import calculate_metrics, make_difference_image
from cognishield.protector import ProtectionConfig, protect_image
from cognishield.provenance import sign_image, verify_image


def main() -> int:
    parser = argparse.ArgumentParser(description="CogniShield image protection pipeline")
    parser.add_argument("image", type=Path, help="Input image path")
    parser.add_argument("--epsilon", type=float, default=8.0 / 255.0, help="Max perturbation, 0-1 scale")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--qualities", type=int, nargs="+", default=[95, 75, 50])
    args = parser.parse_args()

    ensure_project_dirs()
    original = load_rgb_image(args.image)
    config = ProtectionConfig(
        epsilon=args.epsilon,
        seed=args.seed,
        iterations=args.iterations,
        jpeg_qualities=tuple(q for q in args.qualities if q >= 50),
    )
    protected, noise_preview = protect_image(original, config)

    run_dir = OUTPUT_DIR / args.image.stem
    run_dir.mkdir(parents=True, exist_ok=True)
    protected_path = run_dir / "protected.png"
    noise_path = run_dir / "noise_preview.png"
    diff_path = run_dir / "difference_x12.png"
    protected.save(protected_path)
    noise_preview.save(noise_path)
    make_difference_image(original, protected).save(diff_path)
    save_jpeg_variants(protected, run_dir, args.qualities)

    metrics = calculate_metrics(original, protected).to_dict()
    compression = {
        str(q): metric.to_dict()
        for q, metric in evaluate_compression(original, protected, args.qualities).items()
    }
    manifest_path = sign_image(
        protected_path,
        KEY_DIR,
        metadata={"epsilon": args.epsilon, "iterations": args.iterations, "seed": args.seed},
    )
    verification = verify_image(protected_path, manifest_path, KEY_DIR)

    report = {
        "input": str(args.image),
        "protected": str(protected_path),
        "noise_preview": str(noise_path),
        "difference": str(diff_path),
        "metrics": metrics,
        "compression": compression,
        "provenance_manifest": str(manifest_path),
        "verification": verification.__dict__,
    }
    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

