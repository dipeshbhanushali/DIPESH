"""IonParams (every value a setting, JSON), datasets (storage times from
names, frame lists, discovery, saving with the settings), background
choice and geometry."""
import json
import os

import numpy as np
import pytest

from dipesh.ion_analysis import (IonDataset, IonParams, LEGACY, PileupMethod,
                                 find_datasets, format_frames, load,
                                 parse_frames, parse_storage_time, save)
from dipesh.ion_analysis.background import choose_frames, median_of
from dipesh.ion_analysis.geometry import masks
from dipesh.ion_analysis.params import (CalibrationParams, RegionParams,
                                        SinglesParams)

import ion_frames


# ── settings ───────────────────────────────────────────────────────────────

def test_defaults_are_general_and_check_out():
    p = IonParams().check()
    assert p.region.kind == "frame" and not p.region.pileup
    assert p.methods == () and p.singles.ties == "reading"
    assert p.background.mode == "darkest"


@pytest.mark.parametrize("p", [IonParams()] + list(LEGACY.values()))
def test_settings_go_through_json_unchanged(p):
    again = IonParams.from_json(p.to_json())
    assert again == p and again.check() == p


def test_a_typo_in_a_saved_file_is_an_error():
    d = IonParams().to_dict()
    d["singles"]["peek_thresh"] = 3
    with pytest.raises(ValueError, match="peek_thresh"):
        IonParams.from_dict(d)


@pytest.mark.parametrize("bad", [
    IonParams(grey="sepia"),
    IonParams(singles=SinglesParams(box=6)),
    IonParams(methods=(PileupMethod(kind="guess"),)),
    IonParams(methods=(PileupMethod(calibration=CalibrationParams(box=10)),)),
    IonParams(methods=(PileupMethod(name="a"), PileupMethod(name="a"))),
])
def test_settings_that_are_not_allowed_are_named(bad):
    with pytest.raises(ValueError):
        bad.check()


# ── storage times and frames ───────────────────────────────────────────────

@pytest.mark.parametrize("name,seconds", [
    ("storage_time_10min.avi", 600),
    ("RF_0_45_storage_time10min.avi", 600),       # not the first number
    ("RF_Amplitude_0_34_EndCap_1000v_storage 45 mins_trimmed.avi", 2700),
    ("storage_time_20s", 20),
    ("storage_time_15min_screen.avi", 900),
    ("1 min 16 sec", 76),
    ("run_1.5h", 5400),
    ("Video_20250328130134873.avi", None),         # a time stamp, no unit
    ("frames", None),
])
def test_storage_time_from_names(name, seconds):
    assert parse_storage_time(name) == seconds


def test_frame_lists():
    assert parse_frames("0-1, 5, 10-12") == [0, 1, 5, 10, 11, 12]
    assert parse_frames(" 3 ;2  2") == [2, 3]
    assert parse_frames("") == []
    assert format_frames([12, 0, 1, 5, 10, 11]) == "0-1, 5, 10-12"
    with pytest.raises(ValueError):
        parse_frames("4-x")


# ── datasets ──────────────────────────────────────────────────────────────

def test_a_folder_of_frames_is_a_dataset_numbered_in_order(tmp_path):
    folder = ion_frames.write(str(tmp_path / "release"), ion_frames.PLAN)
    ds = IonDataset("release", folder)
    assert [it.run_number for it in ds.items()] == list(range(10))
    ds.frames = (2, 8, 2)
    assert [it.run_number for it in ds.items()] == [2, 4, 6]


def test_find_datasets_reads_times_and_takes_overrides(tmp_path):
    import cv2
    for name in ("storage_time_20s", "storage_time_10min", "odd"):
        d = tmp_path / "scan" / name
        d.mkdir(parents=True)
        out = cv2.VideoWriter(str(d / f"{name}.avi"),
                              cv2.VideoWriter_fourcc(*"MJPG"), 5, (32, 32))
        for _ in range(3):
            out.write(np.zeros((32, 32, 3), np.uint8))
        out.release()
    found = {d.name: d for d in find_datasets(str(tmp_path / "scan"),
                                              overrides={"odd": 42})}
    assert {n: d.storage_time for n, d in found.items()} == \
        {"storage_time_20s": 20, "storage_time_10min": 600, "odd": 42}
    assert found["storage_time_20s"].series == "storage_time_20s"


def test_a_dataset_is_saved_with_its_settings(tmp_path):
    ds = IonDataset("a", "x.avi", frames=(0, 50), exclude=(0, 1),
                    storage_time=900, series="transport",
                    background_source="bg.avi")
    p = LEGACY["legacy transport, intensity"]
    save(str(tmp_path / "a.json"), ds, p)
    assert json.loads((tmp_path / "a.json").read_text())["dataset"]["exclude"] == [0, 1]
    assert load(str(tmp_path / "a.json")) == (ds, p)


# ── background and geometry ───────────────────────────────────────────────

def test_background_frames_are_chosen_as_asked():
    numbers = list(range(10, 20))
    light = {f: (f * 7) % 5 for f in numbers}      # ties on purpose
    assert choose_frames(numbers, "all") == numbers
    assert choose_frames(numbers, "random", 0) == numbers
    assert choose_frames(numbers, "darkest", 50, light=light) == numbers
    dark = choose_frames(numbers, "darkest", 4, light=light)
    assert dark == [10, 13, 15, 18]                 # light 0 and 1
    import random
    picked = choose_frames(numbers, "random", 3, seed=42)
    want = sorted(numbers[k] for k in random.Random(42).sample(range(10), 3))
    assert picked == want


def test_the_median_of_whole_counts_is_exact():
    frames = [np.full((4, 4), v, np.float32) for v in (3, 9, 4, 8)]
    assert np.all(median_of(frames) == 6.0)         # (4 + 8) / 2
    frames = [np.full((2, 2), v, np.float32) for v in (0.25, 0.75, 0.5)]
    assert np.all(median_of(frames) == 0.5)          # not whole: float


def test_regions():
    shape = (60, 80)
    assert masks(shape, RegionParams()) == (None, None)
    rect, disc = masks(shape, RegionParams("rect", x0=10, y0=5, x1=20, y1=8))
    assert rect.sum() == 30 and rect[5, 10] and not rect[8, 10] and disc is None
    ring, disc = masks(shape, RegionParams("ring", cx=40, cy=30, r=20,
                                           inner_cx=42, inner_cy=30, inner_r=5))
    assert disc[30, 42] and not ring[30, 42] and ring[30, 55] and not ring[30, 75]
    assert not (ring & disc).any()
