from __future__ import annotations

import sys
import json
from multiprocessing import Process, Queue
from pathlib import Path
from queue import Empty
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cognishield.compression import evaluate_compression, jpeg_roundtrip
from cognishield.config import KEY_DIR, MODEL_DIR, OUTPUT_DIR, ensure_project_dirs
from cognishield.metrics import calculate_metrics, make_difference_image
from cognishield.protector import ProtectionConfig, protect_image
from cognishield.provenance import sign_image, verify_image
from cognishield.sd_turbo import SDTurboTester


PROJECT_ROOT = Path(__file__).resolve().parent
WEB_OUTPUT_DIR = OUTPUT_DIR / "web"
EVALUATION_OUTPUT_DIR = OUTPUT_DIR / "evaluations"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024


def _is_allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _as_float(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)


def _safe_int(value: str | None, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value or default)))
    except (TypeError, ValueError):
        return default


def _latest_evaluation() -> tuple[str, dict[str, object]] | None:
    if not EVALUATION_OUTPUT_DIR.exists():
        return None
    summaries = sorted(EVALUATION_OUTPUT_DIR.glob("*/summary.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for summary_path in summaries:
        try:
            return summary_path.parent.name, json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return None


def _sd_turbo_worker(
    model_dir: str,
    original_path: str,
    protected_path: str,
    output_dir: str,
    prompt: str,
    seed: int,
    result_queue: Queue,
) -> None:
    """Run the optional heavy model outside the web server process.

    CUDA or model-loading failures can end a Python process without raising a normal
    exception. Keeping the work here protects the upload API from those failures.
    """
    try:
        tester = SDTurboTester(Path(model_dir))
        original_result = tester.run(Image.open(original_path).convert("RGB"), prompt=prompt, seed=seed)
        protected_result = tester.run(Image.open(protected_path).convert("RGB"), prompt=prompt, seed=seed)
        output_path = Path(output_dir)
        original_model_path = output_path / "sd_turbo_original.png"
        protected_model_path = output_path / "sd_turbo_protected.png"
        original_result.image.save(original_model_path)
        protected_result.image.save(protected_model_path)
        result_queue.put(
            {
                "ok": True,
                "device": original_result.device,
                "original_name": original_model_path.name,
                "protected_name": protected_model_path.name,
            }
        )
    except Exception as exc:
        result_queue.put({"ok": False, "error": str(exc)})


def _run_sd_turbo_safely(
    original_path: Path, protected_path: Path, run_dir: Path, prompt: str, seed: int
) -> tuple[dict[str, str] | None, str | None]:
    if not MODEL_DIR.exists():
        return None, f"SD-Turbo model directory not found: {MODEL_DIR}"

    result_queue: Queue = Queue()
    worker = Process(
        target=_sd_turbo_worker,
        args=(str(MODEL_DIR), str(original_path), str(protected_path), str(run_dir), prompt, seed, result_queue),
        daemon=True,
    )
    worker.start()
    worker.join(timeout=300)

    if worker.is_alive():
        worker.terminate()
        worker.join(timeout=10)
        return None, "SD-Turbo did not finish within five minutes. The image protection result is still available."
    if worker.exitcode != 0:
        return None, "SD-Turbo stopped unexpectedly. Check your NVIDIA driver and available GPU memory, then try again."

    try:
        result = result_queue.get(timeout=5)
    except Empty:
        return None, "SD-Turbo ended without returning a result. The image protection result is still available."
    finally:
        result_queue.close()

    if not result["ok"]:
        return None, result["error"]
    return (
        {
            "device": result["device"],
            "original_url": f"/results/{run_dir.name}/{result['original_name']}",
            "protected_url": f"/results/{run_dir.name}/{result['protected_name']}",
        },
        None,
    )


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/how-it-works")
def how_it_works() -> str:
    return render_template("how_it_works.html")


@app.get("/evaluation")
def evaluation() -> str:
    latest = _latest_evaluation()
    if latest is None:
        return render_template("evaluation.html", run_name=None, summary=None, charts=False, report=False)
    run_name, summary = latest
    run_dir = EVALUATION_OUTPUT_DIR / run_name
    return render_template(
        "evaluation.html",
        run_name=run_name,
        summary=summary,
        charts=(run_dir / "evaluation_charts.png").exists(),
        report=(run_dir / "report.md").exists(),
    )


@app.post("/api/protect")
def protect():
    uploaded = request.files.get("image")
    if uploaded is None or not uploaded.filename:
        return jsonify(error="Choose an image before protecting it."), 400
    if not _is_allowed_file(uploaded.filename):
        return jsonify(error="Use a PNG, JPG, JPEG, or WEBP image."), 400

    epsilon_255 = _safe_int(request.form.get("epsilon"), 8, 1, 16)
    iterations = _safe_int(request.form.get("iterations"), 4, 0, 8)
    seed = _safe_int(request.form.get("seed"), 42, 0, 999999)
    qualities = sorted(
        {int(value) for value in request.form.getlist("qualities") if value in {"95", "85", "75", "60", "50"}},
        reverse=True,
    ) or [95, 75]
    run_model = request.form.get("run_model") == "true"
    prompt = request.form.get("prompt", "a realistic portrait photograph, natural lighting").strip()

    try:
        original = Image.open(uploaded.stream).convert("RGB")
        original.load()
    except (UnidentifiedImageError, OSError, ValueError):
        return jsonify(error="The selected file could not be read as an image."), 400

    ensure_project_dirs()
    run_id = uuid4().hex[:12]
    run_dir = WEB_OUTPUT_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        config = ProtectionConfig(epsilon=epsilon_255 / 255.0, seed=seed, iterations=iterations, jpeg_qualities=tuple(qualities))
        protected, noise_preview = protect_image(original, config)
        diff_image = make_difference_image(original, protected)
        metrics = calculate_metrics(original, protected)
        compression_metrics = evaluate_compression(original, protected, qualities)

        original_path = run_dir / "original.png"
        protected_path = run_dir / "protected.png"
        noise_path = run_dir / "noise_preview.png"
        diff_path = run_dir / "difference_x12.png"
        original.save(original_path)
        protected.save(protected_path)
        noise_preview.save(noise_path)
        diff_image.save(diff_path)

        manifest_path = sign_image(
            protected_path,
            KEY_DIR,
            metadata={"source_filename": secure_filename(uploaded.filename), "epsilon": epsilon_255 / 255.0, "epsilon_pixels": epsilon_255, "iterations": iterations, "seed": seed, "jpeg_qualities": qualities},
        )
        verification = verify_image(protected_path, manifest_path, KEY_DIR)

        jpeg_images = []
        for quality in qualities:
            jpeg_path = run_dir / f"protected_jpeg_q{quality}.jpg"
            jpeg_roundtrip(protected, quality).save(jpeg_path, format="JPEG", quality=quality)
            jpeg_images.append({"quality": quality, "url": f"/results/{run_id}/{jpeg_path.name}"})

        model_result: dict[str, str] | None = None
        model_error: str | None = None
        if run_model:
            model_result, model_error = _run_sd_turbo_safely(
                original_path, protected_path, run_dir, prompt, seed
            )

        return jsonify(
            success=True,
            images={"original": f"/results/{run_id}/{original_path.name}", "protected": f"/results/{run_id}/{protected_path.name}", "difference": f"/results/{run_id}/{diff_path.name}", "noise": f"/results/{run_id}/{noise_path.name}"},
            downloads={"protected": f"/download/{run_id}/{protected_path.name}", "provenance": f"/download/{run_id}/{manifest_path.name}"},
            metrics={"psnr": _as_float(metrics.psnr), "ssim": _as_float(metrics.ssim), "mse": _as_float(metrics.mse), "mean_abs_delta": _as_float(metrics.mean_abs_delta), "max_abs_delta": _as_float(metrics.max_abs_delta)},
            compression=[{"quality": quality, "psnr": _as_float(item.psnr), "ssim": _as_float(item.ssim), "mse": _as_float(item.mse)} for quality, item in compression_metrics.items()],
            jpeg_images=jpeg_images,
            provenance={"valid": verification.valid, "reason": verification.reason, "hash": verification.image_hash},
            model=model_result,
            model_error=model_error,
        )
    except Exception as exc:
        return jsonify(error=f"Protection could not be completed: {exc}"), 500


@app.get("/results/<run_id>/<path:filename>")
def result_file(run_id: str, filename: str):
    return send_from_directory(WEB_OUTPUT_DIR / run_id, filename)


@app.get("/download/<run_id>/<path:filename>")
def download_file(run_id: str, filename: str):
    return send_from_directory(WEB_OUTPUT_DIR / run_id, filename, as_attachment=True)


@app.get("/evaluation-files/<run_name>/<path:filename>")
def evaluation_file(run_name: str, filename: str):
    return send_from_directory(EVALUATION_OUTPUT_DIR / run_name, filename)


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify(error="That file is larger than the 200 MB upload limit."), 413


if __name__ == "__main__":
    ensure_project_dirs()
    app.run(host="127.0.0.1", port=5000, debug=False)
