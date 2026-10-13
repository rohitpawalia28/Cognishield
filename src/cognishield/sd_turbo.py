from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from PIL import Image

from .image_io import resize_for_model


@dataclass(frozen=True)
class SDTurboResult:
    image: Image.Image
    device: str
    prompt: str
    strength: float
    steps: int


class SDTurboTester:
    def __init__(self, model_dir: Path, max_side: int = 512) -> None:
        self.model_dir = model_dir
        self.max_side = max_side
        self._pipe = None
        self._device = "cpu"

    def load(self) -> None:
        if self._pipe is not None:
            return

        try:
            import torch
            from diffusers import AutoPipelineForImage2Image
        except Exception as exc:
            raise RuntimeError(
                "Install AI dependencies first: torch, diffusers, transformers, accelerate, safetensors."
            ) from exc

        if not self.model_dir.exists():
            raise FileNotFoundError(f"SD-Turbo model directory not found: {self.model_dir}")

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self._device == "cuda" else torch.float32
        self._pipe = AutoPipelineForImage2Image.from_pretrained(
            str(self.model_dir),
            torch_dtype=dtype,
            local_files_only=True,
        )
        self._pipe.to(self._device)
        if hasattr(self._pipe, "enable_attention_slicing"):
            self._pipe.enable_attention_slicing()

    def run(
        self,
        image: Image.Image,
        prompt: str,
        strength: float = 0.55,
        steps: int = 2,
        seed: int = 42,
    ) -> SDTurboResult:
        self.load()

        import torch

        safe_strength = min(max(strength, 0.05), 1.0)
        effective_steps = max(2, steps, math.ceil(1.0 / safe_strength))
        prepared = resize_for_model(image, self.max_side)
        generator = torch.Generator(device=self._device).manual_seed(seed)
        result = self._pipe(
            prompt=prompt,
            image=prepared,
            num_inference_steps=effective_steps,
            strength=safe_strength,
            guidance_scale=0.0,
            generator=generator,
        ).images[0]
        return SDTurboResult(
            image=result,
            device=self._device,
            prompt=prompt,
            strength=safe_strength,
            steps=effective_steps,
        )
