"""Recursive discovery of video files under a root folder."""
from __future__ import annotations

from pathlib import Path


def find_videos(root: Path, extensions: list[str], skip_dirs: set[str] | None = None) -> list[Path]:
    """Recursively find video files under root.

    skip_dirs is matched against directory *names* anywhere in the relative path, so the
    configured review folders (which live inside source_folder) are never re-scanned on
    subsequent runs.
    """
    skip_dirs = skip_dirs or set()
    exts = {e.lower() for e in extensions}
    results: list[Path] = []

    for path in root.rglob("*"):
        if path.is_dir():
            continue
        relative_parts = path.relative_to(root).parts[:-1]
        if any(part in skip_dirs for part in relative_parts):
            continue
        if path.suffix.lower() in exts:
            results.append(path)

    return sorted(results)
