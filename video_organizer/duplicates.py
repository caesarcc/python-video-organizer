"""Duplicate and probable-duplicate detection.

Two passes, run in order so a video is never claimed by both:
  1. Exact duplicates - grouped by SHA-256 of the file content.
  2. Probable duplicates - among whatever is left, cluster by "duration within tolerance AND
     perceptual hash of a sampled frame within threshold".

This module never touches the filesystem beyond reading files to hash them - it only returns
DuplicateGroup data. Turning that into moves is cli.py's job, and mover.py is the only place a
move actually happens.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

from .config import DuplicatesConfig
from .hashing import perceptual_hash, sha256_file
from .metadata import VideoMetadata, probe

T = TypeVar("T")


@dataclass
class DuplicateGroup:
    videos: list[VideoMetadata]
    reason: str  # human-readable explanation shown in the review table


def _group_by_key(items: list[T], key_fn: Callable[[T], object]) -> list[list[T]]:
    groups: dict[object, list[T]] = {}
    for item in items:
        groups.setdefault(key_fn(item), []).append(item)
    return [g for g in groups.values() if len(g) > 1]


def find_duplicate_groups(paths: list[Path], config: DuplicatesConfig) -> list[DuplicateGroup]:
    metadatas: list[VideoMetadata] = []
    for p in paths:
        try:
            metadatas.append(probe(p))
        except Exception:
            # A file ffprobe can't read just won't be compared against anything.
            continue

    groups: list[DuplicateGroup] = []
    claimed: set[Path] = set()

    # Pass 1: identical file content.
    for group in _group_by_key(metadatas, lambda v: sha256_file(v.path)):
        groups.append(DuplicateGroup(videos=group, reason="identical file content"))
        claimed.update(v.path for v in group)

    # Pass 2: similar duration + matching sampled frame, among what's left.
    remaining = [v for v in metadatas if v.path not in claimed]
    hashed = [(v, perceptual_hash(v.path, v.duration_seconds)) for v in remaining]

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
    """Pick the filename stem believed to carry the most information (the longest one), used as
    the shared base name when renaming a group's copies for side-by-side review."""
    best = max(group.videos, key=lambda v: len(v.path.stem))
    return best.path.stem
