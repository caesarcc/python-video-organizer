from pathlib import Path

from video_organizer import duplicates as duplicates_module
from video_organizer.config import DuplicatesConfig
from video_organizer.duplicates import DuplicateGroup, find_duplicate_groups, pick_reference_name
from video_organizer.metadata import VideoMetadata


def _meta(path, duration=10.0):
    return VideoMetadata(
        path=Path(path), size_bytes=100, duration_seconds=duration, width=1920, height=1080, created_at=1_700_000_000.0
    )


def test_pick_reference_name_prefers_longer_stem():
    group = DuplicateGroup(
        videos=[_meta("a.mp4"), _meta("a_much_more_descriptive_name.mp4")],
        reason="test",
    )
    assert pick_reference_name(group) == "a_much_more_descriptive_name"


def test_find_duplicate_groups_by_exact_hash(monkeypatch, tmp_path):
    file_a = tmp_path / "a.mp4"
    file_b = tmp_path / "b.mp4"
    file_a.write_bytes(b"same content")
    file_b.write_bytes(b"same content")

    monkeypatch.setattr(duplicates_module, "probe", lambda p: _meta(p))
    monkeypatch.setattr(duplicates_module, "perceptual_hash", lambda *a, **k: None)

    groups = find_duplicate_groups([file_a, file_b], DuplicatesConfig())

    assert len(groups) == 1
    assert groups[0].reason == "identical file content"
    assert {v.path for v in groups[0].videos} == {file_a, file_b}


def test_find_duplicate_groups_ignores_distinct_files(monkeypatch, tmp_path):
    file_a = tmp_path / "a.mp4"
    file_b = tmp_path / "b.mp4"
    file_a.write_bytes(b"content one")
    file_b.write_bytes(b"content two, totally different")

    monkeypatch.setattr(duplicates_module, "probe", lambda p: _meta(p))
    monkeypatch.setattr(duplicates_module, "perceptual_hash", lambda *a, **k: None)

    groups = find_duplicate_groups([file_a, file_b], DuplicatesConfig())

    assert groups == []
