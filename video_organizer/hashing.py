"""File hashing helpers used for duplicate detection.

sha256_file() catches byte-identical copies. perceptual_hash() catches "probable" duplicates:
re-encodes, re-muxes, or renamed copies of the same footage that will never share a byte hash but
look the same when you sample a frame.
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
    """Extract a representative frame and return its perceptual hash, or None if unavailable."""
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
