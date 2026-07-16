"""Carrega e valida o arquivo de configuração do video-organizer."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_VIDEO_EXTENSIONS = [
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
]


class ConfigError(RuntimeError):
    """Lançada quando o config.yaml está ausente ou inválido."""


@dataclass
class DuplicatesConfig:
    enabled: bool = True
    review_folder_name: str = "_duplicates_review"
    hash_distance_threshold: int = 8
    duration_tolerance_seconds: float = 2.0


@dataclass
class ShortVideosConfig:
    enabled: bool = True
    review_folder_name: str = "_short_videos"
    max_duration_seconds: float = 5.0


@dataclass
class Config:
    source_folder: Path
    source_folder_from_default: bool = False
    video_extensions: list[str] = field(default_factory=lambda: list(DEFAULT_VIDEO_EXTENSIONS))
    duplicates: DuplicatesConfig = field(default_factory=DuplicatesConfig)
    short_videos: ShortVideosConfig = field(default_factory=ShortVideosConfig)
    confirm_before_move: bool = True

    @property
    def duplicates_review_path(self) -> Path:
        return self.source_folder / self.duplicates.review_folder_name

    @property
    def short_videos_review_path(self) -> Path:
        return self.source_folder / self.short_videos.review_folder_name


def load_config(path: Path) -> Config:
    if not path.exists():
        raise ConfigError(
            f"Config file not found: {path}\n"
            f"Copy config.example.yaml to {path.name} and edit it first."
        )

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    raw_source_folder = raw.get("source_folder")
    if raw_source_folder:
        source_folder = Path(raw_source_folder).expanduser()
        source_folder_from_default = False
    else:
        # source_folder é opcional: se ausente, usa a pasta atual de onde o comando é executado.
        source_folder = Path.cwd()
        source_folder_from_default = True

    if not source_folder.is_dir():
        raise ConfigError(f"source_folder does not exist or is not a directory: {source_folder}")

    dup_raw = raw.get("duplicates") or {}
    duplicates = DuplicatesConfig(
        enabled=dup_raw.get("enabled", True),
        review_folder_name=dup_raw.get("review_folder_name", "_duplicates_review"),
        hash_distance_threshold=dup_raw.get("hash_distance_threshold", 8),
        duration_tolerance_seconds=dup_raw.get("duration_tolerance_seconds", 2.0),
    )

    short_raw = raw.get("short_videos") or {}
    short_videos = ShortVideosConfig(
        enabled=short_raw.get("enabled", True),
        review_folder_name=short_raw.get("review_folder_name", "_short_videos"),
        max_duration_seconds=short_raw.get("max_duration_seconds", 5.0),
    )

    return Config(
        source_folder=source_folder,
        source_folder_from_default=source_folder_from_default,
        video_extensions=[e.lower() for e in raw.get("video_extensions", DEFAULT_VIDEO_EXTENSIONS)],
        duplicates=duplicates,
        short_videos=short_videos,
        confirm_before_move=raw.get("confirm_before_move", True),
    )
