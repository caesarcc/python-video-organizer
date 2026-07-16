"""Detecção de vídeos mais curtos que uma duração configurada."""
from __future__ import annotations

from pathlib import Path

from rich.console import Console

from .config import ShortVideosConfig
from .metadata import probe

console = Console()


def find_short_videos(paths: list[Path], config: ShortVideosConfig) -> list[Path]:
    short: list[Path] = []
    total = len(paths)
    for i, p in enumerate(paths, start=1):
        console.print(f"[dim]({i}/{total})[/dim] Checking duration: {p.name}")
        try:
            meta = probe(p)
        except Exception:
            console.print(f"[yellow]  skipped (unreadable metadata): {p.name}[/yellow]")
            continue
        if 0 < meta.duration_seconds < config.max_duration_seconds:
            short.append(p)
    return short
