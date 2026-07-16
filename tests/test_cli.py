import video_organizer.cli as cli_module
from video_organizer.config import Config


def _make_config(source_folder):
    return Config(source_folder=source_folder, source_folder_from_default=False)


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
