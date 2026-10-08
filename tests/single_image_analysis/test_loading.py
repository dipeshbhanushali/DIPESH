"""Finding runs and images on disk, reading images and Batman parameters."""
import cv2
import numpy as np

from dipesh import (find_run_folders, find_tiff, load_image,
                                 parse_batman, scan)


def test_scan_handles_run_folders_loose_images_and_files(tmp_path, run_folder,
                                                         frame):
    runs = tmp_path / "runs"
    runs.mkdir()
    run_folder(runs, 512089)
    run_folder(runs, 512090)
    assert [i.run_number for i in scan(str(runs))] == [512089, 512090]

    loose = tmp_path / "loose"
    loose.mkdir()
    for k in range(3):
        cv2.imwrite(str(loose / f"frame_{k:03d}.png"),
                    frame(2, seed=k)[0].astype(np.uint8))
    assert len(scan(str(loose))) == 3
    assert len(scan(str(loose / "frame_000.png"))) == 1


def test_scan_of_a_single_run_folder_gives_one_item(tmp_path, run_folder):
    d, _ = run_folder(tmp_path, 517890)
    items = scan(str(d))
    assert len(items) == 1 and items[0].run_number == 517890
    assert items[0].folder == str(d)


def test_scan_of_nothing_useful_is_empty(tmp_path):
    (tmp_path / "notes.txt").write_text("x")
    assert scan(str(tmp_path)) == []
    assert scan(str(tmp_path / "notes.txt")) == []
    assert scan(str(tmp_path / "missing")) == []


def test_run_folders_are_sorted_by_run_number(tmp_path):
    for rn in (30, 4, 12):
        (tmp_path / f"pbar_run_{rn}").mkdir()
    (tmp_path / "other").mkdir()
    assert [rn for rn, _ in find_run_folders(str(tmp_path))] == [4, 12, 30]


def test_the_tiff_is_found_one_folder_down(tmp_path):
    sub = tmp_path / "camera"
    sub.mkdir()
    cv2.imwrite(str(sub / "camera_x.tiff"), np.zeros((8, 8), np.uint8))
    assert find_tiff(str(tmp_path)).endswith("camera_x.tiff")
    assert find_tiff(str(tmp_path / "missing")) is None


def test_an_image_is_read_at_its_own_bit_depth(tmp_path):
    img = (np.arange(64, dtype=np.uint16).reshape(8, 8) * 60)
    cv2.imwrite(str(tmp_path / "a.tiff"), img)
    got = load_image(str(tmp_path / "a.tiff"))
    assert got.dtype == np.float32 and np.array_equal(got, img)
    assert load_image(str(tmp_path / "nope.tiff")) is None


def test_batman_parameters_are_read(tmp_path, run_folder):
    d, _ = run_folder(tmp_path, 1, batman={"ExtLine_MCP": 1650, "PT_TrapTime": 5000})
    assert parse_batman(str(d)) == {"ExtLine_MCP": 1650.0, "PT_TrapTime": 5000.0}


def test_a_missing_or_broken_batman_gives_no_parameters(tmp_path):
    assert parse_batman(str(tmp_path)) == {}
    (tmp_path / "Batman.json").write_text("not json")
    assert parse_batman(str(tmp_path)) == {}
