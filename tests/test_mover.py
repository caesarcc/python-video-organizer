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


def test_unique_destination_avoids_in_memory_collisions(tmp_path):
    # Nenhum dos dois arquivos existe no disco ainda (são MovePlans de um mesmo lote não
    # executado), então a checagem precisa considerar o conjunto reserved, não só o disco.
    reserved = set()
    target = tmp_path / "clip.mp4"

    first = unique_destination(target, reserved)
    second = unique_destination(target, reserved)

    assert first == tmp_path / "clip.mp4"
    assert second == tmp_path / "clip (1).mp4"
    assert reserved == {first, second}
