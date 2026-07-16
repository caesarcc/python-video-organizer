"""Busca recursiva de arquivos de vídeo a partir de uma pasta raiz."""
from __future__ import annotations

from pathlib import Path


def find_videos(root: Path, extensions: list[str], skip_dirs: set[str] | None = None) -> list[Path]:
    """Busca vídeos recursivamente a partir de root.

    skip_dirs é comparado com os *nomes* de pasta em qualquer ponto do caminho relativo, para que
    as pastas de revisão configuradas (que ficam dentro de source_folder) nunca sejam
    reescaneadas nas próximas execuções.
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
