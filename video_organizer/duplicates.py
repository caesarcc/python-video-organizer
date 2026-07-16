"""Detecção de duplicados e prováveis duplicados.

Duas passagens, executadas em ordem para que um vídeo nunca seja reivindicado pelas duas:
  1. Duplicados exatos - agrupados pelo SHA-256 do conteúdo do arquivo.
  2. Prováveis duplicados - entre o que sobrou, agrupa por "duração dentro da tolerância E
     hash perceptual de um frame amostrado dentro do limite".

Este módulo nunca toca o sistema de arquivos além de ler os arquivos para gerar os hashes - ele
só retorna dados de DuplicateGroup. Transformar isso em movimentações é responsabilidade do
cli.py, e mover.py é o único lugar onde uma movimentação de fato acontece.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from .config import DuplicatesConfig
from .hashing import perceptual_hash, sha256_file
from .metadata import VideoMetadata, probe

console = Console()


@dataclass
class DuplicateGroup:
    videos: list[VideoMetadata]
    reason: str  # explicação legível exibida na tabela de revisão


def find_duplicate_groups(paths: list[Path], config: DuplicatesConfig) -> list[DuplicateGroup]:
    total = len(paths)
    metadatas: list[VideoMetadata] = []
    for i, p in enumerate(paths, start=1):
        console.print(f"[dim]({i}/{total})[/dim] Reading metadata: {p.name}")
        try:
            metadatas.append(probe(p))
        except Exception:
            # Um arquivo que o ffprobe não consegue ler simplesmente não será comparado com nada.
            console.print(f"[yellow]  skipped (unreadable metadata): {p.name}[/yellow]")
            continue

    groups: list[DuplicateGroup] = []
    claimed: set[Path] = set()

    # Passagem 1: conteúdo de arquivo idêntico.
    hashes: dict[str, list[VideoMetadata]] = {}
    for i, v in enumerate(metadatas, start=1):
        console.print(f"[dim]({i}/{len(metadatas)})[/dim] Hashing (SHA-256): {v.path.name}")
        hashes.setdefault(sha256_file(v.path), []).append(v)

    for group in hashes.values():
        if len(group) > 1:
            groups.append(DuplicateGroup(videos=group, reason="identical file content"))
            claimed.update(v.path for v in group)

    # Passagem 2: duração parecida + frame amostrado correspondente, entre o que sobrou.
    remaining = [v for v in metadatas if v.path not in claimed]
    hashed = []
    for i, v in enumerate(remaining, start=1):
        console.print(f"[dim]({i}/{len(remaining)})[/dim] Sampling frame for perceptual hash: {v.path.name}")
        hashed.append((v, perceptual_hash(v.path, v.duration_seconds)))

    used: set[Path] = set()
    for i, (v1, h1) in enumerate(hashed):
        if v1.path in used or h1 is None:
            continue
        cluster = [v1]
        for v2, h2 in hashed[i + 1:]:
            if v2.path in used or h2 is None:
                continue
            if abs(v1.duration_seconds - v2.duration_seconds) > config.duration_tolerance_seconds:
                continue
            if (h1 - h2) <= config.hash_distance_threshold:
                cluster.append(v2)
        if len(cluster) > 1:
            groups.append(DuplicateGroup(videos=cluster, reason="similar duration and matching sampled frame"))
            used.update(v.path for v in cluster)

    return groups


def pick_reference_name(group: DuplicateGroup) -> str:
    """Escolhe o nome de arquivo (sem extensão) que parece carregar mais informação (o mais
    longo), usado como nome base compartilhado ao renomear as cópias do grupo para revisão lado
    a lado."""
    best = max(group.videos, key=lambda v: len(v.path.stem))
    return best.path.stem
