"""The app with files of every kind: what is skipped is logged and counted,
folders at any depth become datasets, video frames can be stepped through."""
import os

import cv2
import numpy as np
import pytest

from dipesh.single_image_analysis import close_videos
from gui import live_result, page, run_all


def grey(path, level=20):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = np.full((64, 80), level, np.uint8)
    img[30:34, 30:34] = 240
    cv2.imwrite(str(path), img)


@pytest.fixture
def logged(window):
    seen = []
    window.s.logged.connect(lambda level, msg: seen.append((level, msg)))
    return seen


def test_every_skipped_file_gets_a_log_line_and_the_summary_counts_them(
        window, qtbot, tmp_path, logged):
    grey(tmp_path / "a.png")
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "anim.gif").write_bytes(b"GIF89a")
    with live_result(window, qtbot):
        window.sidebar.add_paths([str(tmp_path)])
    lines = [m for lev, m in logged if lev == "warn" and m.startswith("skipped")]
    assert len(lines) == 2
    assert any("notes.txt: .txt files are not read" in m for m in lines)
    assert window.sidebar.summary.text() == "1 images, 0 counted, 2 skipped"


def test_dropped_files_that_cannot_be_read_are_logged(window, tmp_path, logged):
    (tmp_path / "notes.txt").write_text("x")
    window.sidebar.add_paths([str(tmp_path / "notes.txt"),
                              str(tmp_path / "missing.png")])
    msgs = [m for _, m in logged]
    assert any(m.startswith("skipped") and "notes.txt" in m for m in msgs)
    assert any("missing.png: not found" in m for m in msgs)
    assert window.s.datasets == []
    assert window.sidebar.summary.text() == "2 skipped"


def test_a_nested_folder_gives_one_dataset_per_folder(window, qtbot, tmp_path):
    root = tmp_path / "data"
    grey(root / "bg" / "a.png")
    grey(root / "bg" / "b.bmp")
    grey(root / "ions" / "day" / "c.jpg")
    run = root / "scan" / "pbar_run_12"
    grey(run / "camera.tiff")
    with live_result(window, qtbot):
        window.sidebar.add_paths([str(root)])
    got = {d.name: [i.name for i in d.items] for d in window.s.datasets}
    assert got == {"bg": ["a", "b"], "day": ["c"], "scan": ["12"]}
    run_all(window, qtbot)
    assert window.sidebar.summary.text() == "4 images, 4 counted"


@pytest.fixture
def video(tmp_path):
    p = tmp_path / "clip.avi"
    out = cv2.VideoWriter(str(p), cv2.VideoWriter_fourcc(*"MJPG"), 5, (80, 64))
    for k in range(8):
        img = np.full((64, 80), 20, np.uint8)
        img[30:34, 5 + 8 * k:9 + 8 * k] = 240
        out.write(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
    out.release()
    yield p
    close_videos()


def test_the_frames_of_a_video_can_be_stepped_through(window, qtbot, video):
    with live_result(window, qtbot):
        window.sidebar.add_paths([str(video)])
    ds = window.s.datasets[0]
    assert [i.name for i in ds.items] == [f"clip.avi [frame {k}]"
                                          for k in range(8)]
    image = page(window, "image")
    seen = []
    for k in range(1, 4):
        with live_result(window, qtbot):
            window.sidebar.step(1)
        assert window.s.current[1].frame == k
        seen.append(int(np.argmax(image._img[32])))
    assert seen[0] < seen[1] < seen[2]                  # the spot moves


def test_a_frame_range_can_be_chosen_for_a_video_dataset(window, qtbot, video):
    with live_result(window, qtbot):
        window.sidebar.add_paths([str(video)])
    ds = window.s.datasets[0]
    run_all(window, qtbot)
    kept = ds.results[ds.items[2].key]
    window.sidebar.set_frames(ds, range(2, 8, 3))
    assert [i.frame for i in ds.items] == [2, 5]
    assert set(ds.results) == {i.key for i in ds.items}  # the others go
    assert ds.results[ds.items[0].key] is kept           # kept ones stay
    assert window.sidebar.tree.topLevelItem(0).childCount() == 2


def test_the_frame_dialog_gives_a_range(qapp):
    from dipesh.graphical_interface.widgets import FrameRangeDialog
    d = FrameRangeDialog(31)
    assert d.frames() == range(0, 31)
    d.first.setValue(4); d.last.setValue(20); d.every.setValue(5)
    assert list(d.frames()) == [4, 9, 14, 19]
    d.deleteLater()
