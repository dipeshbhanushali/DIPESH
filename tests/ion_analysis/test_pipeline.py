"""The ion analysis on synthetic release videos with known ions and a known
pile-up disc (tests/helpers/ion_frames.py): exact counts, the background,
the SIS equal to the light put into one ion, each pile-up method against a
hand calculation, fallbacks, exclusions, several methods side by side."""
import dataclasses

import cv2
import numpy as np
import pytest

from dipesh.ion_analysis import IonDataset, IonParams, analyse
from dipesh.ion_analysis.params import (AggregateParams, BackgroundParams,
                                        CalibrationParams, PileupMethod,
                                        RegionParams, SinglesParams)
from dipesh.single_image_analysis import close_videos

import ion_frames as F

RING = RegionParams("ring", cx=F.CENTRE[0], cy=F.CENTRE[1], r=F.OUTER_R,
                    inner_cx=F.CENTRE[0], inner_cy=F.CENTRE[1],
                    inner_r=F.DISC_R)
SINGLES = SinglesParams(peak_thresh=12, box=7, box_thresh=50, min_dist=9)
BOX = CalibrationParams(measure="box", box=11)


def params(*methods, region=RING, **kw):
    return IonParams(background=BackgroundParams(mode="all"), region=region,
                     singles=SINGLES, methods=tuple(methods), **kw)


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    return F.write(str(tmp_path_factory.mktemp("ions") / "release"), F.PLAN)


@pytest.fixture(scope="module")
def plain(tmp_path_factory):
    """The same frames without the pile-up (on the whole frame a pile-up is
    just more light, found as spots)."""
    return F.write(str(tmp_path_factory.mktemp("ions") / "plain"),
                   F.PLAN_NO_DISC)


DISC_IONS = round(F.disc_light(30) / F.ION_LIGHT)    # 30


def singles_per_frame():
    return [n for n, _ in F.PLAN]


# ── B1: background, single ions, exclusions ──────────────────────────────

def test_the_background_is_the_pattern_and_single_ions_are_exact(plain):
    r = analyse(IonDataset("r", plain), params(region=RegionParams()))
    assert np.array_equal(r.background, F.pattern())
    assert [row.singles for row in r.rows] == singles_per_frame()
    total = r.totals["single ions"]
    assert (total.count, total.frames) == (sum(singles_per_frame()), 10)
    first = r.ions[1][0]
    assert first[2] == 60 and first[3] == F.ION_LIGHT        # peak, box sum


def test_in_a_ring_the_disc_is_not_counted_as_single_ions(video):
    r = analyse(IonDataset("r", video), params())
    assert [row.singles for row in r.rows] == singles_per_frame()


@pytest.mark.parametrize("ties", ["reading", "numpy1"])
def test_both_tie_orders_give_the_same_here(plain, ties):
    p = params(region=RegionParams())
    p = p.with_(singles=dataclasses.replace(p.singles, ties=ties))
    assert [row.singles for row in analyse(IonDataset("r", plain), p).rows] \
        == singles_per_frame()


def test_excluded_frames_are_marked_and_left_out_of_every_total(video):
    ds = IonDataset("r", video, exclude=(3, 7))
    r = analyse(ds, params(PileupMethod(name="a", calibration=BOX)))
    assert r.excluded == [3, 7]
    assert [row.excluded for row in r.rows] == [k in (3, 7) for k in range(10)]
    want = sum(n for k, (n, _) in enumerate(F.PLAN) if k not in (3, 7))
    t = r.totals["a"]
    assert (t.singles, t.inner, t.frames) == (want, 0, 8)


def test_a_frame_range_and_a_separate_background(video, plain):
    """Frames 1-5 alone have ions at the same places in 3 of 5 frames: their
    own median would hold the ions, so the background comes from the whole
    folder, given as a separate background source."""
    ds = IonDataset("r", video, frames=(1, 6), background_source=plain)
    r = analyse(ds, params().with_(background=BackgroundParams(mode="video")))
    assert [row.frame for row in r.rows] == [1, 2, 3, 4, 5]
    assert np.array_equal(r.background, F.pattern())
    assert r.totals["single ions"].count == 5 + 12 + 8


def test_a_video_works_too(tmp_path):
    p = str(tmp_path / "clip.avi")
    out = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"MJPG"), 5,
                          (F.SIZE, F.SIZE))
    for n, disc in F.PLAN:
        out.write(cv2.cvtColor(F.frame(F.SITES[:n], disc), cv2.COLOR_GRAY2BGR))
    out.release()
    try:
        r = analyse(IonDataset("clip", p), params())
        assert [row.singles for row in r.rows] == singles_per_frame()
    finally:
        close_videos()


def test_progress_and_cancel(video):
    from dipesh.ion_analysis import Cancelled
    seen = []
    analyse(IonDataset("r", video), params(),
            progress=lambda done, total: seen.append((done, total)))
    assert seen[-1] == (10, 10)
    with pytest.raises(Cancelled):
        analyse(IonDataset("r", video), params(), cancelled=lambda: True)


# ── B2: calibration, pile-up, aggregation ─────────────────────────────────

DISC_FRAME = 3                                       # 12 single ions + disc


def test_the_sis_is_the_light_of_one_ion(video):
    aperture = CalibrationParams(measure="aperture", radius=3)
    r = analyse(IonDataset("r", video),
                params(PileupMethod(name="box", calibration=BOX),
                       PileupMethod(name="aperture", calibration=aperture)))
    for row in r.rows:
        if row.singles:
            assert row.methods["box"].sis == F.ION_LIGHT
            assert row.methods["aperture"].sis == F.ION_LIGHT
        else:
            assert row.methods["box"].sis is None


def test_threshold_sum_counts_the_disc(video):
    m = PileupMethod(name="t", kind="threshold_sum", pixel_thresh=10,
                     calibration=BOX)
    r = analyse(IonDataset("r", video), params(m))
    row = r.rows[DISC_FRAME].methods["t"]
    light = F.disc_light(30)
    assert row.signal == light
    assert row.inner == round(light / F.ION_LIGHT) == DISC_IONS
    assert row.total == 12 + DISC_IONS
    assert r.totals["t"].count == sum(singles_per_frame()) + DISC_IONS
    # pixels at or below the threshold are not counted
    m2 = dataclasses.replace(m, name="t2", pixel_thresh=F.disc_per_pixel(30))
    r2 = analyse(IonDataset("r", video), params(m2))
    assert r2.rows[DISC_FRAME].methods["t2"].signal == 0


def test_baseline_sum_takes_a_percentile_of_the_disc_off(video):
    m = PileupMethod(name="b", kind="baseline_sum", baseline="percentile",
                     baseline_percentile=95, rounding="none", calibration=BOX)
    r = analyse(IonDataset("r", video), params(m))
    light = F.disc_light(30)
    sums = [0.0] * 9 + [light]                         # one frame has light
    base = float(np.percentile(sums, 95))
    assert r.methods["b"].baseline == base
    assert r.rows[DISC_FRAME].methods["b"].inner == pytest.approx(
        (light - base) / F.ION_LIGHT)
    fixed = dataclasses.replace(m, baseline="fixed", baseline_value=100.0)
    r = analyse(IonDataset("r", video), params(fixed))
    assert r.rows[DISC_FRAME].methods["b"].signal == light - 100


def test_corrected_sum_takes_the_background_per_pixel_off(video):
    cal = dataclasses.replace(BOX, background="fixed", background_value=0.5)
    m = PileupMethod(name="c", kind="corrected_sum", min_sum=50,
                     rounding="none", calibration=cal)
    r = analyse(IonDataset("r", video), params(m))
    npix = F.disc_mask().sum()
    row = r.rows[DISC_FRAME].methods["c"]
    assert row.signal == F.disc_light(30) - 0.5 * npix
    # the SIS has the same background taken off: 121 pixels in the box
    assert row.sis == F.ION_LIGHT - 0.5 * 121
    assert row.inner == pytest.approx(row.signal / row.sis)
    # empty discs: S = -0.5 npix, below min_sum: no blob
    assert all(rr.methods["c"].inner == 0 for k, rr in enumerate(r.rows)
               if k != DISC_FRAME)


def test_the_sparsest_background_is_measured_away_from_ions(tmp_path):
    plan = [(n, d) for n, d in F.PLAN]
    folder = F.write(str(tmp_path / "v"), plan)
    cal = dataclasses.replace(BOX, background="sparsest", sparsest_frames=3)
    r = analyse(IonDataset("v", folder),
                params(PileupMethod(name="s", kind="corrected_sum",
                                    calibration=cal)))
    # after an exact background every quiet pixel is 0
    assert r.methods["s"].background_per_pixel == 0.0


def test_one_sis_for_all_frames(video):
    cal = dataclasses.replace(BOX, scope="frames", min_ions=6)
    r = analyse(IonDataset("r", video),
                params(PileupMethod(name="f", calibration=cal)))
    assert r.methods["f"].sis == F.ION_LIGHT
    assert {rr.methods["f"].sis for rr in r.rows} == {F.ION_LIGHT}


@pytest.mark.parametrize("fallback,inner,frames", [
    ("none", 0, 10), ("fixed", DISC_IONS, 10),
    ("skip", 0, 3)])            # skip: every frame without single ions
def test_a_frame_without_single_ions_uses_the_fallback(tmp_path, fallback,
                                                      inner, frames):
    plan = list(F.PLAN)
    plan[DISC_FRAME] = (0, 30)                       # a disc, no single ions
    folder = F.write(str(tmp_path / "v"), plan)
    cal = dataclasses.replace(BOX, fallback=fallback, fixed_value=F.ION_LIGHT)
    r = analyse(IonDataset("v", folder),
                params(PileupMethod(name="x", calibration=cal)))
    row = r.rows[DISC_FRAME].methods["x"]
    assert row.inner == inner and row.skipped == (fallback == "skip")
    assert r.totals["x"].frames == frames
    assert r.totals["x"].inner == inner


def test_several_methods_side_by_side_and_the_active_rule(video):
    ms = (PileupMethod(name="t", calibration=BOX),
          PileupMethod(name="c", kind="corrected_sum", rounding="none",
                       calibration=BOX))
    r = analyse(IonDataset("r", video), params(*ms))
    assert set(r.totals) == {"t", "c"}
    assert r.totals["c"].inner == pytest.approx(F.disc_light(30) / F.ION_LIGHT)
    active = analyse(IonDataset("r", video),
                     params(*ms, aggregate=AggregateParams("active", 6.0)))
    # frames 1 (5 ions) and 7 (3 ions) are not above 6
    assert active.totals["t"].frames == 2
    assert active.totals["t"].count == 12 + DISC_IONS + 8


def test_isolated_selection(video):
    cal = dataclasses.replace(BOX, select="isolated", isolation_px=25)
    r = analyse(IonDataset("r", video),
                params(PileupMethod(name="i", calibration=cal)))
    # the ions are 20 px apart: none is isolated by 25 px; one alone is
    assert r.rows[DISC_FRAME].methods["i"].sis is None


def test_the_background_is_kept_until_its_frames_change(tmp_path):
    from dipesh.ion_analysis import run
    folder = F.write(str(tmp_path / "v"), F.PLAN_NO_DISC)
    ds = IonDataset("v", folder)
    first = analyse(ds, params()).background
    again = analyse(ds, params(PileupMethod(name="m", calibration=BOX)))
    assert again.background is first                  # not made again
    import os
    import time
    cv2.imwrite(os.path.join(folder, "frame_00000.png"),
                F.frame([], 0) + 1)                    # the frames change
    later = time.time() + 2
    os.utime(os.path.join(folder, "frame_00000.png"), (later, later))
    assert analyse(ds, params()).background is not first
    run.forget_backgrounds()


def test_recount_with_other_frames_left_out_equals_a_new_analysis(video):
    from dipesh.ion_analysis import recount
    ms = (PileupMethod(name="t", calibration=BOX),
          PileupMethod(name="b", kind="baseline_sum", baseline_percentile=50,
                       calibration=dataclasses.replace(BOX, scope="frames")))
    first = analyse(IonDataset("r", video), params(*ms))
    again = recount(first, (1, 3))
    fresh = analyse(IonDataset("r", video, exclude=(1, 3)), params(*ms))
    assert again.dataset.exclude == (1, 3) and first.dataset.exclude == ()
    assert again.totals == fresh.totals
    assert [r.methods for r in again.rows] == [r.methods for r in fresh.rows]
    assert again.methods == fresh.methods
    assert first.totals != again.totals              # the first is unchanged
