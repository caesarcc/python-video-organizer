"""Funções de hash usadas na detecção de duplicados.

sha256_file() identifica cópias idênticas byte a byte. perceptual_hash() identifica duplicados
"prováveis": cópias recodificadas, remuxadas ou renomeadas da mesma gravação, que nunca vão
compartilhar o mesmo hash de bytes, mas parecem iguais ao comparar um frame amostrado.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import imagehash
from PIL import Image

FFMPEG = shutil.which("ffmpeg")

_HASH_CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def perceptual_hash(path: Path, duration_seconds: float, at_fraction: float = 0.5) -> Optional[imagehash.ImageHash]:
    """Extrai um frame representativo e retorna seu hash perceptual, ou None se indisponível."""
    if FFMPEG is None or duration_seconds <= 0:
        return None

    timestamp = max(duration_seconds * at_fraction, 0.0)

    with tempfile.TemporaryDirectory() as tmp:
        frame_path = Path(tmp) / "frame.jpg"
        cmd = [
            FFMPEG, "-y", "-ss", str(timestamp), "-i", str(path),
            "-frames:v", "1", "-q:v", "2", str(frame_path),
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0 or not frame_path.exists():
            return None

        with Image.open(frame_path) as img:
            return imagehash.phash(img)
