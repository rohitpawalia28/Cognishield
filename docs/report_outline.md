# CogniShield Report Outline

## 1. Problem Statement

Generative AI tools can manipulate images before victims know the attack has happened. Existing detection systems react after fake content has already been generated or shared. CogniShield shifts protection earlier by immunizing images locally before upload.

## 2. Objectives

- Add low-visibility perturbations to images.
- Preserve human visual quality.
- Test robustness against JPEG compression.
- Verify protected image integrity using cryptographic provenance.
- Evaluate selected target generative model behavior on original and protected images.

## 3. Threat Model

The attacker has access to an image uploaded online and tries to transform it using a generative image-to-image model. The defender protects the image before upload. The first target model for this prototype is local SD-Turbo image-to-image.

## 4. System Modules

- Image preprocessing
- Compression-aware perturbation generator
- Quality metric evaluator
- JPEG robustness evaluator
- Ed25519 provenance signer/verifier
- Streamlit demonstration app
- Optional SD-Turbo target-model tester

## 5. Evaluation Metrics

- PSNR between original and protected image
- SSIM between original and protected image
- Mean absolute pixel delta
- Max absolute pixel delta
- PSNR/SSIM after JPEG quality 95, 75, and 50
- Visual comparison of SD-Turbo output before and after protection

## 6. Experimental Procedure

1. Collect 10-20 permitted test images.
2. Run `run_batch.py` on all images.
3. Record visual quality metrics.
4. Test JPEG compression levels.
5. Run SD-Turbo comparison on selected examples.
6. Verify provenance signature for protected outputs.

## 7. Limitations

- The current perturbation generator is a prototype and not guaranteed to defeat every model.
- Strong cropping, resizing, denoising, or screenshots may weaken perturbations.
- Provenance proves byte integrity after signing, not objective real-world truth.
- Mobile deployment is future work after the local prototype is validated.

## 8. Future Work

- Add target-model gradient optimization.
- Add face-swap model evaluation.
- Convert protection pipeline to ONNX or TFLite.
- Add watermarking in addition to sidecar cryptographic signatures.
- Test against social media upload/download transformations.

