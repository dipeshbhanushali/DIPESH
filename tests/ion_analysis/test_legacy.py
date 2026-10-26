"""
The general ion analysis with the legacy presets repeats earlier analyses
exactly, on the real videos.

The data are found under the folder in the environment variable
DIPESH_ION_DATA (default C:\\Dipesh\\giovanni\\data); without it these tests
are skipped. They only read it. The expected numbers are the earlier
outputs in that folder, and totals listed in ION_PIPELINE_REVIEW.md
(section 6.4).

The storage-time series has nine videos (about 20 s each): by default the
first is analysed again, frame by frame; set DIPESH_ION_FULL=1 for all
nine. The decay fit of the nine counts is tested in test_decay.py.
"""
import csv
import os

import pytest

from dipesh.ion_analysis import IonDataset, LEGACY, analyse, find_datasets
from dipesh.single_image_analysis import close_videos

DATA = os.environ.get("DIPESH_ION_DATA", r"C:\Dipesh\giovanni\data")
FULL = os.environ.get("DIPESH_ION_FULL") == "1"

pytestmark = pytest.mark.skipif(not os.path.isdir(DATA),
                                reason=f"no ion data in {DATA}")


def path(*parts):
    p = os.path.join(DATA, *parts)
    if not os.path.exists(p):
        pytest.skip(f"missing {p}")
    return p


def rows(*parts):
    with open(path(*parts), newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(autouse=True)
def _close():
    yield
    close_videos()


# ── the release video on the whole frame (45 min) ─────────────────────────

def test_release_whole_frame():
    ds = IonDataset("45 min", path(
        "45 min data",
        "RF_Amplitude_0_34_EndCap_1000v_storage 45 mins_trimmed.avi"))
    r = analyse(ds, LEGACY["legacy release, whole frame"])
    old = rows("45 min data", "ion_counts", "ion_counts.csv")
    assert [row.singles for row in r.rows] == [int(o["ion_count"]) for o in old]
    assert r.totals["single ions"].count == 1168


# ── the transport video, two methods for the pile-up disc (15 min) ────────

@pytest.fixture(scope="module")
def transport():
    """The release clip, frames 0 and 1 left out of the totals as in the
    earlier result; the background from the full video."""
    return IonDataset(
        "15 min", path("15 min storage data", "1 min 16 sec",
                       "Video_20250328130702154_trimmed.avi"),
        storage_time=900, exclude=(0, 1),
        background_source=path("15 min storage data", "15 min",
                               "Video_20250328130702154_trimmed.avi"))


@pytest.fixture(scope="module")
def intensity(transport):
    return analyse(transport, LEGACY["legacy transport, intensity"])


def test_transport_intensity_every_frame(intensity):
    r = intensity
    old = {o["frame"]: o for o in
           rows("15 min intensity", "ion_counts_15mins.csv")}   # frames 2-18
    for row in r.rows:
        m = row.methods["intensity"]
        o = old.get(f"frame_{row.frame:05d}.png")
        if o is None:
            continue
        assert (row.singles, m.inner, m.total) == (
            int(o["outer_ions"]), int(o["intensity_method_count"]),
            int(o["total_ions"])), row.frame
        assert m.sis_ions == int(o["calib_ions_used"])
        assert m.signal == pytest.approx(float(o["inner_signal_sum"]), abs=0.5)
    # frames 0 and 1 are not in that file: from the earlier run of the code
    assert [(r.rows[k].singles, r.rows[k].methods["intensity"].inner)
            for k in (0, 1)] == [(2663, 114), (718, 86)]


def test_transport_intensity_totals(intensity):
    assert intensity.excluded == [0, 1]
    assert intensity.totals["intensity"].count == 3815
    every = sum(row.methods["intensity"].total for row in intensity.rows)
    assert every == 7396                    # with no frame left out


def test_transport_luminosity(transport):
    r = analyse(transport, LEGACY["legacy transport, luminosity"])
    info = r.methods["luminosity"]
    assert info.background_per_pixel == 10.0
    assert info.sis == 368.4
    old = {int(o["frame_index"]): o for o in
           rows("15 min luminosity", "inner_ion_estimates.csv")}
    for row in r.rows:
        m = row.methods["luminosity"]
        assert row.singles == int(old[row.frame]["num_outer_ions"])
        assert m.signal == float(old[row.frame]["inner_corrected_sum"])
        assert m.inner == pytest.approx(
            float(old[row.frame]["estimated_inner_ions"]), abs=0.005)
    assert r.totals["luminosity"].count == pytest.approx(4171.05, abs=0.01)


# ── the storage-time series (5 fps) ───────────────────────────────────────

STORAGE = {20: ("20s", 1596), 60: ("1min", 1517), 180: ("3min", 987),
           300: ("5min", 1061), 420: ("7min", 777), 600: ("10min", 906),
           900: ("15min", 1018), 1200: ("20min", 578), 1800: ("30min", 897)}
QUICK = (20,)


@pytest.fixture(scope="module")
def storage_videos():
    found = [d for d in find_datasets(path("storage analysis",
                                           "Yes_Old_filter_No_switch", "5fps"))
             if d.path.lower().endswith(".avi")]
    return {int(d.storage_time): d for d in found}


def test_the_storage_series_is_found_with_its_times(storage_videos):
    assert sorted(storage_videos) == sorted(STORAGE)


@pytest.mark.parametrize("seconds", [
    pytest.param(s, marks=() if s in QUICK or FULL else pytest.mark.skip(
        reason="set DIPESH_ION_FULL=1 for every video of the series"))
    for s in sorted(STORAGE)])
def test_storage_video(storage_videos, seconds):
    tag, total = STORAGE[seconds]
    r = analyse(storage_videos[seconds], LEGACY["legacy storage"])
    old = rows("storage analysis", "5fps_old_filter", "analysis_output_5fps",
               f"5fps_old_filter_{tag}", "ion_counts", "ion_counts.csv")
    assert len(old) == len(r.rows)
    for o, row in zip(old, r.rows):
        assert (row.singles, row.methods["baseline"].inner) == (
            int(o["outer_ions"]), int(o["intensity_method_count"])), row.frame
    assert r.totals["baseline"].count == total
