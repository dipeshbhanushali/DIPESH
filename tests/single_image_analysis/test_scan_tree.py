"""scan_tree(): folders at any depth become datasets."""
import json
import os

import cv2
import numpy as np

from dipesh import DetectionParams, analyse, scan_tree


def image(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.full((32, 32), 20, np.uint8))


def batman(folder, **kw):
    s = " ".join(f"{k}={v}" for k, v in kw.items())
    (folder / "Batman.json").write_text(json.dumps([{"Batman": {"__value": s}}]))


def names(datasets):
    return {name: [i.name for i in items] for name, items in datasets}


def test_every_folder_of_loose_files_is_a_dataset_named_after_it(tmp_path):
    root = tmp_path / "data"
    image(root / "day1" / "bg" / "a.png")
    image(root / "day1" / "bg" / "b.png")
    image(root / "day1" / "ions" / "deep" / "deeper" / "c.tif")
    image(root / "top.png")
    got, skipped = scan_tree(str(root))
    assert names(got) == {"data": ["top"], "bg": ["a", "b"],
                          "deeper": ["c"]}
    assert skipped == []


def test_folders_of_runs_keep_their_batman_and_runs(tmp_path):
    root = tmp_path / "data"
    for rn, bias in ((517890, 100), (517891, 200)):
        d = root / "scan" / f"pbar_run_{rn}-06-08-2026.JDIR"
        image(d / "camera.tiff")
        batman(d, ExtLine_TrapBiasGround=bias)
    got, _ = scan_tree(str(root))
    (name, items), = got
    assert name == "scan"
    assert [i.run_number for i in items] == [517890, 517891]
    r = analyse(items[1], DetectionParams())
    assert r.batman == {"ExtLine_TrapBiasGround": 200.0}


def test_run_folders_are_not_entered_as_datasets_of_their_own(tmp_path):
    d = tmp_path / "scan" / "pbar_run_1"
    image(d / "camera" / "frame.tiff")              # the camera subfolder
    got, _ = scan_tree(str(tmp_path / "scan"))
    assert names(got) == {"scan": ["1"]}


def test_metadata_is_optional_everywhere(tmp_path):
    image(tmp_path / "scan" / "pbar_run_7" / "x.tiff")       # no Batman
    image(tmp_path / "plain" / "y.png")
    got, _ = scan_tree(str(tmp_path))
    by = dict(got)
    for items in by.values():
        r = analyse(items[0], DetectionParams())
        assert r.ok and r.batman == {} and r.pickup == {}


def test_a_folder_with_a_batman_file_is_one_run(tmp_path):
    d = tmp_path / "data" / "odd_name"
    image(d / "camera.tiff")
    batman(d, PT_TrapTime=5000)
    got, _ = scan_tree(str(tmp_path / "data"))
    assert names(got) == {"odd_name": ["0"]}
    got, _ = scan_tree(str(d))                      # added on its own
    assert names(got) == {"odd_name": ["0"]}


def test_runs_and_loose_files_in_one_folder_give_two_datasets(tmp_path):
    root = tmp_path / "mixed"
    image(root / "pbar_run_3" / "c.tiff")
    image(root / "overview.png")
    got, _ = scan_tree(str(root))
    assert names(got) == {"mixed": ["3"], "mixed (files)": ["overview"]}


def test_folders_with_the_same_name_are_told_apart_by_their_path(tmp_path):
    root = tmp_path / "data"
    image(root / "monday" / "bg" / "a.png")
    image(root / "tuesday" / "bg" / "b.png")
    got, _ = scan_tree(str(root))
    assert [n for n, _ in got] == ["data/monday/bg", "data/tuesday/bg"]


def test_what_is_not_read_is_reported_at_every_depth(tmp_path):
    root = tmp_path / "data"
    image(root / "a" / "b" / "ok.png")
    (root / "a" / "b" / "notes.txt").write_text("x")
    (root / "c").mkdir(parents=True)
    (root / "c" / "clip.mov").write_bytes(b"x")
    (root / "empty").mkdir()
    got, skipped = scan_tree(str(root))
    assert names(got) == {"b": ["ok"]}
    assert sorted(os.path.basename(p) for p, _ in skipped) == [
        "clip.mov", "notes.txt"]


def test_a_path_that_is_not_a_folder_is_reported(tmp_path):
    got, skipped = scan_tree(str(tmp_path / "missing"))
    assert got == [] and skipped[0].reason == "not a folder"
