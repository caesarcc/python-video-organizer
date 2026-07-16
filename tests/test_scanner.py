from video_organizer.scanner import find_videos


def test_find_videos_recursive_and_filtered(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x")
    (tmp_path / "a.txt").write_bytes(b"x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.MKV").write_bytes(b"x")

    skip = tmp_path / "_skip"
    skip.mkdir()
    (skip / "c.mp4").write_bytes(b"x")

    result = find_videos(tmp_path, [".mp4", ".mkv"], skip_dirs={"_skip"})

    names = sorted(p.name for p in result)
    assert names == ["a.mp4", "b.MKV"]
