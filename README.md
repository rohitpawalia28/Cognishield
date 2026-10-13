# CogniShield

CogniShield is a local prototype for edge-based adversarial immunization of digital images. It protects an input image with small perturbations, measures visual quality trade-offs, tests JPEG compression robustness, and creates cryptographic provenance for the protected output.

## Project Scope

This version focuses on images only. It is designed as a review-ready MVP:

- generate a protected image with imperceptible perturbation
- measure PSNR, SSIM, MSE, mean absolute delta, and max absolute delta
- test protected image quality after JPEG compression
- sign protected image bytes with Ed25519 over SHA-256
- verify whether a protected image has changed after signing
- optionally compare original and protected images through local SD-Turbo

## Folder Layout

```text
Cognishield-main/
  app.py
  run_pipeline.py
  run_batch.py
  requirements.txt
  requirements-core.txt
  requirements-ai.txt
  requirements-torch-cu128.txt
  docs/report_outline.md
  src/cognishield/
  templates/
  static/
  models/sd-turbo/
  outputs/
  keys/
  data/input/
```

## Setup

Fast setup on Windows:

```powershell
.\scripts\setup.ps1
```

Manual setup:

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install PyTorch for NVIDIA CUDA 12.8 wheels:

```powershell
pip install -r requirements-torch-cu128.txt
```

Install the app dependencies:

```powershell
pip install -r requirements-core.txt
pip install -r requirements-ai.txt
```

If PyTorch CUDA installation fails, install the command shown by the official PyTorch selector for your machine and then rerun the app dependency installation.

## Run The Web App

Fast launch:

```powershell
.\scripts\run_app.ps1
```

Manual launch:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open the local URL, usually:

```text
http://127.0.0.1:5000
```

The web interface starts in dark mode and includes a light-mode toggle. It preserves
the original protection, JPEG robustness, provenance signing, downloads, and optional
SD-Turbo target test behavior.

## Run The CLI Pipeline

```powershell
python run_pipeline.py data/input/example.jpg
```

Or:

```powershell
.\scripts\run_cli_example.ps1 data\input\example.jpg
```

## Run Batch Experiments

Put 10-20 permitted images in:

```text
data/input/
```

Then run:

```powershell
.\scripts\run_batch.ps1
```

The batch summary table appears at:

```text
outputs/batch/summary.csv
```

The output appears under:

```text
outputs/example/
```

## SD-Turbo Target Model

The app expects SD-Turbo here:

```text
models/sd-turbo/
```

If the model is not present, the rest of CogniShield still works. Only the optional SD-Turbo target test is disabled.

## What The Provenance Module Proves

The provenance module proves that the protected image bytes match the signed hash. It does not prove that a scene is objectively real. It proves that the image came from this local CogniShield signing key and has not changed since signing.

## Suggested Review Metrics

- PSNR should generally stay above 30 dB for low visible distortion.
- SSIM should generally stay close to 1.0.
- JPEG tests should be reported at quality 95, 75, and 50.
- Attack/model comparison should show original target-model output versus protected target-model output.

---

# Complete Guide: From First Run to Advanced Use

## 1. What CogniShield does

CogniShield is a **local image-protection and provenance prototype**. It takes an image,
creates a subtly modified protected copy, checks how similar that copy is to the original,
tests how the protected copy behaves after JPEG compression, and cryptographically signs
the output.

The project has two independent capabilities:

1. **Image protection and provenance** — available on any supported computer after the core
   dependencies are installed.
2. **SD-Turbo target comparison** — optional; requires a local SD-Turbo model and an
   NVIDIA CUDA GPU for practical performance.

The app runs locally at `127.0.0.1`; the web interface does not upload images to an
external service.

## 2. Main features

- Modern local web interface with dark mode by default and a light-mode toggle.
- PNG, JPG, JPEG, and WEBP upload support (up to 200 MB).
- Edge-aware, high-frequency image perturbation with reproducible seeds.
- JPEG compression robustness testing at 95, 85, 75, 60, and 50 quality.
- PSNR, SSIM, MSE, mean absolute delta, and max absolute delta quality metrics.
- Downloadable protected PNG and signed provenance JSON file.
- Optional original-versus-protected SD-Turbo comparison.
- Command-line processing for one image or an entire folder of images.

## 3. Requirements

### Required for the web app

- Windows 10 or Windows 11
- Python 3.12
- Internet access during the first package installation
- Approximately 2 GB of free disk space for Python packages and output files

### Required only for SD-Turbo

- NVIDIA GPU with a working CUDA driver
- PyTorch CUDA build
- Several GB of additional disk space for the local SD-Turbo model
- Enough GPU memory to load and run the model

The protection, metrics, JPEG tests, provenance, downloads, CLI, and batch workflow do
**not** need SD-Turbo.

## 4. Install Python

If Python is not installed, open PowerShell and run:

```powershell
winget install -e --id Python.Python.3.12
```

Close and reopen PowerShell after installation. Confirm it works:

```powershell
py --version
```

If `py` is not recognised, use the normal Python install path instead:

```powershell
& "$env:LocalAppData\Programs\Python\Python312\python.exe" --version
```

## 5. Install CogniShield

Open PowerShell in the project folder:

```powershell
cd "C:\Users\Rohit Kumar\Documents\Cognishield-main"
```

### Option A — full setup (recommended for NVIDIA / SD-Turbo users)

The project includes a setup script that creates `.venv` and installs the core, CUDA
PyTorch, and AI packages.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

`Bypass` in this command applies only to the open PowerShell window. It does not make a
permanent system-wide policy change.

### Option B — core web app only

Use this path if you only need image protection, metrics, JPEG testing, and provenance.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements-core.txt
```

### Option C — manual full setup

Use this if the setup script is unavailable or you want to see each step.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements-core.txt
.\.venv\Scripts\pip.exe install -r requirements-torch-cu128.txt
.\.venv\Scripts\pip.exe install -r requirements-ai.txt
```

If your GPU uses a different CUDA version, install the appropriate PyTorch build from the
official PyTorch selector, then install `requirements-ai.txt`.

## 6. Start and stop the web application

Start the local server from the project folder:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open this address in a browser:

```text
http://127.0.0.1:5000
```

To stop the server, focus the PowerShell window and press `Ctrl + C`.

To start the app again later, run the same command above. You do not need to reinstall
packages each time.

## 7. Use the web interface

1. Open `http://127.0.0.1:5000`.
2. Click **Choose image**, or drag an image into the upload area.
3. Adjust the protection controls if needed.
4. Click **Protect image**.
5. Review the original and protected images, metrics, compression table, provenance
   verification, and inspection previews.
6. Click **Download protected image** to save the protected PNG.
7. Click **Provenance JSON** to save the signed manifest.

The top-right theme switch changes between dark and light modes. The **How it works** link
opens a same-tab guide showing the full processing flow.

### Control reference

| Control | What it changes | Default | Practical guidance |
| --- | --- | ---: | --- |
| Perturbation budget | Maximum allowed pixel change, from 1 to 16 out of 255 | 8 | Higher is stronger but can be more visible. |
| Compression feedback | Number of JPEG-aware refinement steps | 4 | Higher may improve JPEG resilience but takes longer. |
| Seed | Random-noise starting point | 42 | Keep it fixed for repeatable results. |
| JPEG tests | Compression qualities to evaluate | 95, 75, 50 | Select qualities that match the way images will be shared. |
| Run SD-Turbo target test | Runs both versions through the local SD-Turbo model | Off | Enable only after model setup. |
| Target prompt | Prompt used by the optional SD-Turbo test | Portrait prompt | Use the same prompt for a fair original/protected comparison. |

## 8. How the protection pipeline works

The following is the actual processing sequence:

```text
Input image
    ↓
Convert to RGB float pixel array
    ↓
Create seeded high-frequency noise
    ↓
Create an edge mask from image detail
    ↓
Limit noise to the selected perturbation budget
    ↓
Apply JPEG compression feedback for selected qualities
    ↓
Create protected PNG, noise preview, and magnified difference image
    ↓
Measure quality and JPEG robustness
    ↓
SHA-256 hash → Ed25519 signature → provenance JSON manifest
```

### Protection method

CogniShield creates a seeded high-frequency noise field. It calculates a simple edge mask
from brightness gradients so detailed regions receive more of the allowed change than flat
regions. Every value is clipped to the selected epsilon budget, which prevents large pixel
changes.

When compression feedback is enabled, the protected candidate is JPEG-compressed at the
selected qualities. The difference caused by compression is fed back into the perturbation
for the selected number of iterations. This is intended to help the protection remain
present after a JPEG round trip.

## 9. Understanding results and metrics

### Output images

| File / view | Meaning |
| --- | --- |
| Original image | The uploaded source image converted to RGB. |
| Protected image | The final protected PNG. |
| Difference ×12 | Absolute original-versus-protected difference amplified twelve times for inspection. |
| Noise preview | A visible representation of perturbation intensity. |
| JPEG preview | Protected image after re-encoding at a selected JPEG quality. |

### Metric definitions

| Metric | Desired direction | Meaning |
| --- | --- | --- |
| PSNR | Higher | Pixel-level similarity; values above 30 dB often indicate low visible distortion. |
| SSIM | Closer to 1.0 | Structural similarity between the original and protected images. |
| MSE | Lower | Mean squared pixel error. |
| Mean absolute delta | Lower | Average absolute per-pixel change. |
| Max absolute delta | Lower | Largest absolute change at any pixel/channel. |

Metrics describe similarity, not whether an image is objectively real, safe, or immune to
every transformation.

## 10. Provenance and verification

For every protected PNG, CogniShield:

1. Calculates a SHA-256 hash of the image bytes.
2. Creates or reuses a local Ed25519 key pair in `keys/`.
3. Signs the hash using the private key.
4. Stores the hash, signature, metadata, signing timestamp, and public-key filename in a
   `.provenance.json` manifest.
5. Immediately verifies the signature against the protected image.

The manifest proves that the exact protected image bytes match the signature generated by
the local key. It does not prove who took a photograph, that a scene is real, or that the
file was never copied.

> Keep `keys/cognishield_private.pem` private. Anyone with this private key can create
> signatures that appear to come from this CogniShield installation.

## 11. Enable the optional SD-Turbo target test

The SD-Turbo option is disabled by default. Normal protection works without it.

### Step 1 — install the AI dependencies

If you used the full setup script, this is already done. Otherwise run:

```powershell
.\.venv\Scripts\pip.exe install -r requirements-torch-cu128.txt
.\.venv\Scripts\pip.exe install -r requirements-ai.txt
```

### Step 2 — download the local model

Run this from the project root:

```powershell
.\.venv\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='stabilityai/sd-turbo', local_dir='models/sd-turbo')"
```

The model must be available at:

```text
models/sd-turbo/
```

### Step 3 — use it in the app

1. Restart `app.py` after the download completes.
2. Upload an image.
3. Tick **Run SD-Turbo target test**.
4. Enter a target prompt.
5. Protect the image.

CogniShield sends the original and protected copies through SD-Turbo using the same prompt
and seed, then displays both model outputs. This comparison is optional and does not alter
the protected PNG or its provenance signature.

If the app reports that SD-Turbo is unavailable, verify the model path, NVIDIA driver,
CUDA/PyTorch compatibility, and available GPU memory. The main protection result remains
available even when the optional model test fails.

## 12. Command-line use

### Process one image

```powershell
.\.venv\Scripts\python.exe run_pipeline.py data\input\example.jpg
```

Use custom settings when needed:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py data\input\example.jpg --epsilon 0.03137 --seed 42 --iterations 4 --qualities 95 75 50
```

`--epsilon` is on a 0–1 scale for the CLI. For example, the web default of 8/255 is about
`0.03137`.

Single-image outputs are written to:

```text
outputs/<input-file-name>/
```

That folder includes `protected.png`, `noise_preview.png`, `difference_x12.png`, JPEG
variants, the provenance manifest, and `report.json`.

### Batch process a folder

1. Add permitted PNG, JPG, JPEG, or WEBP files inside `data/input/`.
2. Run:

```powershell
.\.venv\Scripts\python.exe run_batch.py --input-dir data\input
```

3. Read the summary at:

```text
outputs/batch/summary.csv
```

Each image also receives its own output folder under `outputs/batch/`.

## 13. Project structure

```text
app.py                         Flask server and protection API
templates/index.html           Main web interface
templates/how_it_works.html    Same-tab user guide page
static/css/style.css           Responsive themes and layout
static/js/app.js               Upload, controls, API calls, UI effects
src/cognishield/protector.py   Edge-aware protection algorithm
src/cognishield/metrics.py     PSNR, SSIM, MSE, and difference image
src/cognishield/compression.py JPEG round trips and robustness checks
src/cognishield/provenance.py  SHA-256 and Ed25519 signing/verification
src/cognishield/sd_turbo.py    Optional local SD-Turbo runner
run_pipeline.py                Single-image CLI pipeline
run_batch.py                   Folder/batch pipeline
outputs/                       Generated results (ignored by Git)
keys/                          Local signing keys (ignored by Git)
models/                        Downloaded SD-Turbo model (ignored by Git)
```

## 14. Troubleshooting

| Problem | Fix |
| --- | --- |
| `python` or `py` is not recognised | Install Python 3.12, close PowerShell, reopen it, then try again. |
| PowerShell blocks `.ps1` files | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that PowerShell window. |
| `.venv` executable is missing | Recreate the virtual environment and reinstall the dependencies. |
| Browser cannot open the app | Start `app.py` and open `http://127.0.0.1:5000`, not a saved HTML file. |
| Port 5000 is already in use | Stop the prior `app.py` terminal with `Ctrl + C`, then start it again. |
| `Failed to fetch` | Restart the server, refresh the browser, and try without SD-Turbo first. |
| SD-Turbo model directory not found | Download the model into `models/sd-turbo/`. |
| SD-Turbo stops unexpectedly | Check GPU driver, CUDA/PyTorch compatibility, and free GPU memory. The protection result should still be available. |
| Browser styling looks old after an update | Press `Ctrl + F5` for a hard refresh. |

## 15. Important limitations and responsible use

CogniShield is a local MVP for image-protection experiments and review demonstrations. It
does not guarantee resistance to every model, image editor, transformation, crop, or
re-encoding pipeline. Always test with the models and sharing paths relevant to your use
case. Use only images you own or are authorised to process.

---

## 16. Latest web interface enhancements

The project now includes a modern, responsive local web interface rather than a Streamlit
screen. The core Python protection logic has not changed; only the presentation and local
web routes were enhanced.

### Interface features

- Dark mode is the initial theme; use the top-right switch to choose light mode.
- Drag-and-drop image upload, upload previews, and a 200 MB image-size limit.
- Subtle audio feedback for supported browser interactions.
- Animated page entry, rising result panels, floating upload icon, processing pulse,
  button shimmer, image hover zoom, and card-hover motion.
- The browser respects `prefers-reduced-motion` to minimise animation for users who have
  requested reduced motion in their operating-system settings.
- The blank result placeholder disappears after an image is protected, allowing the
  original and protected images to use the available result space.
- SD-Turbo result images use contained previews so full generated images are visible rather
  than being cropped.

### New routes

| Page | URL | Purpose |
| --- | --- | --- |
| Main workspace | `http://127.0.0.1:5000/` | Upload, protect, inspect, and download an image. |
| How it works | `http://127.0.0.1:5000/how-it-works` | Explains the complete protection, JPEG, provenance, and SD-Turbo flow. |
| Evaluation Dashboard | `http://127.0.0.1:5000/evaluation` | Shows the newest completed dataset-evaluation run. |

## 17. Check protected output in ChatGPT

After protection completes, the result card includes **Check in ChatGPT** beside the
protected-image and provenance downloads.

When selected, the button:

1. Downloads the protected PNG as `cognishield_protected.png`.
2. Opens `chatgpt.com` in a new browser tab.
3. Copies a prepared comparison prompt to the clipboard when the browser permits it.
4. Shows an in-app reminder explaining the remaining upload step.

For privacy and browser-security reasons, a local website cannot silently upload a file
into a user’s ChatGPT account. In ChatGPT, click **+**, choose **Add photos & files**,
select the newly downloaded protected PNG, and paste the copied prompt. ChatGPT supports
image inputs through that manual attachment workflow. See the [official ChatGPT image-input
guide](https://help.openai.com/en/articles/8400551-chatgpt-image-inputs-faq) for supported
upload behavior and limitations.

The copied prompt asks ChatGPT to analyse the uploaded protected image, create a
photorealistic recreation with matching subject and composition, and describe visible
differences. This is an optional qualitative comparison; it is not part of the cryptographic
provenance guarantee.

## 18. Dataset evaluation pipeline

### Why the evaluation exists

CogniShield is not a classifier, so its results should not be described as a generic
“accuracy.” The evaluation uses clearly defined, repeatable outcome measures instead:

| Measure | Definition |
| --- | --- |
| Quality pass rate | Percentage of protected images meeting the selected PSNR and SSIM quality thresholds. |
| JPEG pass rate | Percentage of images whose selected JPEG variants meet the JPEG SSIM threshold. |
| Target divergence rate | Percentage of SD-Turbo original/protected output pairs that cross the predefined target-output SSIM threshold. |
| Combined success rate | Percentage that meet both the protected-image quality standard and target-divergence standard. |

The target-divergence rate applies only to this fixed SD-Turbo prompt, seed, model, and
threshold protocol. It is not evidence of universal protection against every model.

### Dataset location

Place permitted images in:

```text
data/input/
```

The current suggested experiment uses 500 diverse images. Record the dataset source, image
selection method, and random-selection seed in a presentation or written report.

### Run the 500-image evaluation

Stop the web server first if it is running, so the GPU is available for the evaluation:

```powershell
Ctrl + C
```

From the project root, run:

```powershell
.\.venv\Scripts\python.exe run_evaluation.py --input-dir data\input --run-name coco500
```

The runner loads SD-Turbo once, then processes each original/protected pair with the same
prompt and seed. A 500-image run can take considerable GPU time. Keep PowerShell open and
prevent the computer from sleeping until it prints `Evaluation complete`.

### Evaluation configuration and default criteria

| Setting | Default |
| --- | ---: |
| Image count | All supported images in `data/input/` (500 for the current study) |
| Epsilon | `8/255` |
| Seed | `42` |
| Compression-feedback steps | `4` |
| JPEG qualities | `95, 75, 50` |
| Quality PSNR pass threshold | `30 dB` |
| Quality SSIM pass threshold | `0.95` |
| JPEG SSIM pass threshold | `0.90` |
| SD-Turbo target-output SSIM maximum | `0.80` |

All thresholds are written to the generated `summary.json` and report. Do not change
thresholds after seeing the results without recording the change as a new experiment.

### Evaluation output files

For the command above, outputs appear here:

```text
outputs/evaluations/coco500/
  results.csv             Per-image metrics, pass/fail values, and errors
  summary.json            Machine-readable aggregate summary and configuration
  report.md               Teacher-ready Markdown summary
  evaluation_charts.png   Quality, JPEG, and success-rate charts
  examples/               Representative four-panel comparison images
```

The runner also supports useful options:

```powershell
# Quick quality/JPEG-only test on 10 images (does not run SD-Turbo)
.\.venv\Scripts\python.exe run_evaluation.py --input-dir data\input --max-images 10 --skip-model --run-name quality_smoke_test

# Run the full set with a different, documented target prompt
.\.venv\Scripts\python.exe run_evaluation.py --input-dir data\input --run-name coco500_prompt_v2 --prompt "a realistic landscape photograph, natural lighting"
```

Use a new `--run-name` for every rerun. The script intentionally does not overwrite an
existing evaluation folder.

### View the results in the dashboard

Once evaluation finishes, restart the app:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open:

```text
http://127.0.0.1:5000/evaluation
```

The dashboard automatically displays the newest completed evaluation folder. It provides
the four headline rates, the fixed protocol settings, charts, and downloads for `results.csv`
and `report.md`.

### Suggested presentation statement

After a completed run, replace the placeholders with actual values from the dashboard:

> “Using a 500-image evaluation dataset and a fixed SD-Turbo protocol, CogniShield achieved
> an average protected-image SSIM of **X**, an average PSNR of **Y dB**, a JPEG robustness
> pass rate of **Z%**, and a combined quality-and-target-divergence success rate of **A%**.”

Do not use placeholder values in a final presentation. Report the exact run name, settings,
dataset source, and generated results.

## 19. Additional project files

```text
run_evaluation.py              Reproducible dataset-evaluation runner
templates/evaluation.html      Evaluation Dashboard page
outputs/evaluations/<run>/     One completed experiment and its evidence files
```
