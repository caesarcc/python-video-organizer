from video_organizer.mover import unique_destination


def test_unique_destination_no_collision(tmp_path):
    target = tmp_path / "video.mp4"
    assert unique_destination(target) == target


def test_unique_destination_avoids_collision(tmp_path):
    target = tmp_path / "video.mp4"
    target.write_bytes(b"x")

    result = unique_destination(target)

    assert result == tmp_path / "video (1).mp4"


def test_unique_destination_skips_multiple_collisions(tmp_path):
    (tmp_path / "video.mp4").write_bytes(b"x")
    (tmp_path / "video (1).mp4").write_bytes(b"x")

    result = unique_destination(tmp_path / "video.mp4")

    assert result == tmp_path / "video (2).mp4"
