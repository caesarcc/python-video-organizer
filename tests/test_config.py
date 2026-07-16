from pathlib import Path

import pytest

from video_organizer.config import ConfigError, load_config


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.yaml")


def test_missing_source_folder_key_defaults_to_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config.yaml"
    config_path.write_text("duplicates:\n  enabled: true\n", encoding="utf-8")

    config = load_config(config_path)

    assert config.source_folder == Path.cwd()
    assert config.source_folder_from_default is True


def test_nonexistent_source_folder_raises(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(f"source_folder: {tmp_path / 'nope'}\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(config_path)


def test_valid_config_defaults(tmp_path):
    video_dir = tmp_path / "videos"
    video_dir.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(f"source_folder: {video_dir}\n", encoding="utf-8")

    config = load_config(config_path)

    assert config.source_folder == video_dir
    assert config.source_folder_from_default is False
    assert config.duplicates.review_folder_name == "_duplicates_review"
    assert config.short_videos.max_duration_seconds == 5.0
    assert config.duplicates_review_path == video_dir / "_duplicates_review"
