"""Video metadata extraction via ffprobe."""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

FFPROBE = shutil.which("ffprobe")


class FFProbeNotFoundError(RuntimeError):
    """Raised when ffprobe is not available on PATH."""


@dataclass
class VideoMetadata:
    path: Path
    size_bytes: int
    duration_seconds: float
    width: int
    height: int


def probe(path: Path) -> VideoMetadata:
    """Read duration and resolution for a video file using ffprobe."""
    if FFPROBE is None:
        raise FFProbeNotFoundError(
            "ffprobe was not found on PATH. Install ffmpeg (https://ffmpeg.org/) and make sure "
            "ffprobe is available in your terminal, then try again."
        )

    cmd = [
        FFPROBE, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration",
        "-of", "json",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout)

    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}

    return VideoMetadata(
        path=path,
        size_bytes=path.stat().st_size,
        duration_seconds=float(fmt.get("duration", 0.0) or 0.0),
        width=int(stream.get("width", 0) or 0),
        height=int(stream.get("height", 0) or 0),
    )
