"""Extração de metadados de vídeo via ffprobe."""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

FFPROBE = shutil.which("ffprobe")


class FFProbeNotFoundError(RuntimeError):
    """Lançada quando o ffprobe não está disponível no PATH."""


@dataclass
class VideoMetadata:
    path: Path
    size_bytes: int
    duration_seconds: float
    width: int
    height: int
    created_at: float


def probe(path: Path) -> VideoMetadata:
    """Lê duração e resolução de um arquivo de vídeo usando o ffprobe."""
    if FFPROBE is None:
        raise FFProbeNotFoundError(
            "ffprobe não foi encontrado no PATH. Instale o ffmpeg (https://ffmpeg.org/) e "
            "garanta que o ffprobe esteja disponível no seu terminal, depois tente novamente."
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
    stat = path.stat()

    return VideoMetadata(
        path=path,
        size_bytes=stat.st_size,
        duration_seconds=float(fmt.get("duration", 0.0) or 0.0),
        width=int(stream.get("width", 0) or 0),
        height=int(stream.get("height", 0) or 0),
        # No Windows, st_ctime é a data de criação do arquivo (em outros sistemas seria a data
        # de alteração de metadados) - este projeto assume ambiente Windows.
        created_at=stat.st_ctime,
    )
