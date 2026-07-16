"""Detection of videos shorter than a configured duration."""
from __future__ import annotations

from pathlib import Path

from .config import ShortVideosConfig
from .metadata import probe


def find_short_videos(paths: list[Path], config: ShortVideosConfig) -> list[Path]:
    short: list[Path] = []
    for p in paths:
        try:
            meta = probe(p)
        except Exception:
            continue
        if 0 < meta.duration_seconds < config.max_duration_seconds:
            short.append(p)
    return short
