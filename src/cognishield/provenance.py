from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


PRIVATE_KEY_FILE = "cognishield_private.pem"
PUBLIC_KEY_FILE = "cognishield_public.pem"


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    reason: str
    image_hash: str | None = None


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_keys(key_dir: Path) -> tuple[Path, Path]:
    key_dir.mkdir(parents=True, exist_ok=True)
    private_path = key_dir / PRIVATE_KEY_FILE
    public_path = key_dir / PUBLIC_KEY_FILE

    if private_path.exists() and public_path.exists():
        return private_path, public_path

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path


def _load_private_key(path: Path) -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def _load_public_key(path: Path) -> Ed25519PublicKey:
    return serialization.load_pem_public_key(path.read_bytes())


def sign_image(
    image_path: str | Path,
    key_dir: Path,
    metadata: dict[str, Any] | None = None,
) -> Path:
    image_path = Path(image_path)
    private_path, public_path = ensure_keys(key_dir)
    image_hash = sha256_file(image_path)
    private_key = _load_private_key(private_path)
    signature = private_key.sign(bytes.fromhex(image_hash))

    manifest = {
        "project": "CogniShield",
        "algorithm": "Ed25519 over SHA-256(image_bytes)",
        "image_file": image_path.name,
        "image_hash_sha256": image_hash,
        "signature_base64": base64.b64encode(signature).decode("ascii"),
        "public_key_file": public_path.name,
        "signed_at_utc": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    manifest_path = image_path.with_suffix(image_path.suffix + ".provenance.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def verify_image(image_path: str | Path, manifest_path: str | Path, key_dir: Path) -> VerificationResult:
    image_path = Path(image_path)
    manifest_path = Path(manifest_path)
    public_path = key_dir / PUBLIC_KEY_FILE

    if not image_path.exists():
        return VerificationResult(False, "Image file does not exist.")
    if not manifest_path.exists():
        return VerificationResult(False, "Provenance manifest does not exist.")
    if not public_path.exists():
        return VerificationResult(False, "Public key does not exist.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    current_hash = sha256_file(image_path)
    recorded_hash = manifest.get("image_hash_sha256")
    if current_hash != recorded_hash:
        return VerificationResult(False, "Image hash changed after signing.", current_hash)

    signature = base64.b64decode(manifest["signature_base64"])
    public_key = _load_public_key(public_path)
    try:
        public_key.verify(signature, bytes.fromhex(current_hash))
    except InvalidSignature:
        return VerificationResult(False, "Signature does not match the public key.", current_hash)

    return VerificationResult(True, "Signature and image hash are valid.", current_hash)

