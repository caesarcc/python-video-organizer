from pathlib import Path

import video_organizer.cli as cli_module
from video_organizer.config import Config, DuplicatesConfig
from video_organizer.duplicates import DuplicateGroup
from video_organizer.metadata import VideoMetadata


def _make_config(source_folder):
    return Config(source_folder=source_folder, source_folder_from_default=False)


def _video(path, duration=12.0, width=1920, height=1080, size=1000, created_at=1_700_000_000.0):
    return VideoMetadata(
        path=Path(path),
        size_bytes=size,
        duration_seconds=duration,
        width=width,
        height=height,
        created_at=created_at,
    )


def test_main_aborts_when_user_declines_initial_confirmation(monkeypatch, tmp_path):
    monkeypatch.setattr(cli_module, "load_config", lambda path: _make_config(tmp_path))
    monkeypatch.setattr(cli_module, "confirm", lambda *a, **k: False)

    def _boom(*a, **k):
        raise AssertionError("find_videos should not run when the user declines the initial confirmation")

    monkeypatch.setattr(cli_module, "find_videos", _boom)

    result = cli_module.main(["--config", str(tmp_path / "config.yaml")])

    assert result == 0


def test_main_proceeds_when_user_confirms(monkeypatch, tmp_path):
    monkeypatch.setattr(cli_module, "load_config", lambda path: _make_config(tmp_path))
    monkeypatch.setattr(cli_module, "confirm", lambda *a, **k: True)
    monkeypatch.setattr(cli_module, "find_videos", lambda *a, **k: [])

    result = cli_module.main(["--config", str(tmp_path / "config.yaml"), "--dry-run"])

    assert result == 0


def test_build_duplicate_plans_keeps_original_filenames(tmp_path):
    config = _make_config(tmp_path)
    group = DuplicateGroup(
        videos=[
            _video(tmp_path / "clip.mp4"),
            _video(tmp_path / "sub" / "a_much_more_descriptive_copy.mp4"),
        ],
        reason="identical file content",
    )

    plans, reports = cli_module.build_duplicate_plans(config, [group])

    dest_names = sorted(p.destination.name for p in plans)
    assert dest_names == ["a_much_more_descriptive_copy.mp4", "clip.mp4"]
    # A pasta do grupo usa o nome mais descritivo, mas os arquivos mantêm o nome original.
    assert all(p.destination.parent.name == "001_a_much_more_descriptive_copy" for p in plans)

    assert len(reports) == 1
    assert reports[0].group_dir.name == "001_a_much_more_descriptive_copy"
    assert str(tmp_path / "clip.mp4") in reports[0].content
    assert str(tmp_path / "sub" / "a_much_more_descriptive_copy.mp4") in reports[0].content
    assert "identical file content" in reports[0].content


def test_build_duplicate_plans_avoids_filename_collisions(tmp_path):
    config = _make_config(tmp_path)
    group = DuplicateGroup(
        videos=[
            _video(tmp_path / "a" / "clip.mp4"),
            _video(tmp_path / "b" / "clip.mp4"),
        ],
        reason="identical file content",
    )

    plans, _ = cli_module.build_duplicate_plans(config, [group])

    dest_names = sorted(p.destination.name for p in plans)
    assert dest_names == ["clip (1).mp4", "clip.mp4"]


def test_build_short_videos_report_has_expected_columns(tmp_path):
    video = _video(tmp_path / "short.mp4", duration=3.5, size=12345, created_at=1_700_000_000.0)

    content = cli_module.build_short_videos_report([video])
    rows = content.splitlines()

    assert rows[0] == "nome_arquivo,caminho_completo_origem,data_criacao_arquivo,tempo_video,tamanho_arquivo"
    assert rows[1].startswith("short.mp4,")
    assert str(video.path.resolve()) in rows[1]
    assert rows[1].endswith("3.50,12345")
