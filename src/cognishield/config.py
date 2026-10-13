from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models" / "sd-turbo"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
KEY_DIR = PROJECT_ROOT / "keys"
DATA_DIR = PROJECT_ROOT / "data"


def ensure_project_dirs() -> None:
    for path in (OUTPUT_DIR, KEY_DIR, DATA_DIR / "input", DATA_DIR / "samples"):
        path.mkdir(parents=True, exist_ok=True)

