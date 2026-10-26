"""The error table (every component against a hand calculation), the decay
fit and two-point tau (with the earlier numbers), and the report files."""
import csv
import json
import math

import numpy as np
import pytest

from dipesh.ion_analysis import IonDataset, IonParams, analyse
from dipesh.ion_analysis.decay import fit_decay, two_point_tau
from dipesh.ion_analysis.errors import ErrorComponent as C, ErrorTable, evaluate
from dipesh.ion_analysis.params import (BackgroundParams, CalibrationParams,
                                        PileupMethod, RegionParams,
                                        SinglesParams)
from dipesh.ion_analysis import report

import ion_frames as F

RING = RegionParams("ring", cx=100, cy=100, r=90, inner_cx=100, inner_cy=100,
                    inner_r=10)
BOX = CalibrationParams(measure="box", box=11)
P = IonParams(background=BackgroundParams(mode="all"), region=RING,
              singles=SinglesParams(peak_thresh=12, box=7, box_thresh=50,
                                    min_dist=9),
              methods=(PileupMethod(name="nearest", calibration=BOX),
                       PileupMethod(name="exact", rounding="none",
                                    calibration=BOX)))


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    folder = F.write(str(tmp_path_factory.mktemp("e") / "v"), F.PLAN)
    return analyse(IonDataset("v", folder, exclude=(7,), storage_time=600),
                   P)


def frame_counts(result, method):
    return [row.methods[method].total for row in result.rows if not row.excluded]


# ── the error table ───────────────────────────────────────────────────────

def test_nothing_is_added_by_default(result):
    e = evaluate(ErrorTable(), result)
    assert (e.statistical, e.systematic, e.total, e.components) == (0, 0, 0, [])
    assert e.method == "nearest"


def test_every_component_by_hand(result):
    n = result.totals["nearest"].count
    exact = result.totals["exact"].count
    frames = frame_counts(result, "nearest")
    per_frame_spread = [abs(a - b) / 2 for a, b in
                        zip(frames, frame_counts(result, "exact"))]
    table = ErrorTable((
        C("counting", "poisson"),
        C("methods", "method_spread", "systematic", spread="half_range"),
        C("methods std", "method_spread", "systematic", spread="std"),
        C("ten percent", "fraction", "systematic", fraction=0.1),
        C("typed", "absolute", "systematic", value=12.5),
        C("frames poisson", "per_frame", per_frame="poisson"),
        C("frames fraction", "per_frame", "systematic", per_frame="fraction",
          fraction=0.2),
        C("frames methods", "per_frame", "systematic",
          per_frame="method_spread", spread="half_range"),
    ), method="nearest")
    e = evaluate(table, result)
    got = {name: v for name, _, v in e.components}
    assert got["counting"] == pytest.approx(math.sqrt(n))
    assert got["methods"] == pytest.approx(abs(n - exact) / 2)
    assert got["methods std"] == pytest.approx(np.std([n, exact], ddof=1))
    assert got["ten percent"] == pytest.approx(0.1 * n)
    assert got["typed"] == 12.5
    assert got["frames poisson"] == pytest.approx(math.sqrt(sum(frames)))
    assert got["frames fraction"] == pytest.approx(
        math.sqrt(sum((0.2 * f) ** 2 for f in frames)))
    assert got["frames methods"] == pytest.approx(
        math.sqrt(sum(s * s for s in per_frame_spread)))
    stat = math.hypot(got["counting"], got["frames poisson"])
    sys_ = math.sqrt(sum(v * v for k, v in got.items()
                         if k not in ("counting", "frames poisson")))
    assert (e.statistical, e.systematic) == (pytest.approx(stat),
                                             pytest.approx(sys_))
    assert e.total == pytest.approx(math.hypot(stat, sys_))


def test_linear_combination(result):
    t = ErrorTable((C("a", "absolute", value=3), C("b", "absolute", value=4),
                    C("c", "absolute", "systematic", value=5)),
                   combine="linear")
    e = evaluate(t, result)
    assert (e.statistical, e.systematic, e.total) == (7, 5, 12)
    e = evaluate(t.__class__(t.components), result)              # quadrature
    assert (e.statistical, e.systematic) == (5, 5)
    assert e.total == pytest.approx(math.sqrt(50))


def test_tables_are_checked_and_saved_with_the_dataset(result, tmp_path):
    with pytest.raises(ValueError):
        ErrorTable((C("a", "guess"),)).check()
    with pytest.raises(ValueError):
        evaluate(ErrorTable(method="missing"), result)
    ds = IonDataset("x", "x.avi", errors=ErrorTable(
        (C("ten percent", "fraction", "systematic", fraction=0.1),)))
    from dipesh.ion_analysis import load, save
    save(str(tmp_path / "x.json"), ds, P)
    assert load(str(tmp_path / "x.json"))[0].errors == ds.errors


# ── decay ─────────────────────────────────────────────────────────────────

STORAGE_T = [20, 60, 180, 300, 420, 600, 900, 1200, 1800]
STORAGE_N = [1596, 1517, 987, 1061, 777, 906, 1018, 578, 897]


def test_the_storage_series_fit_with_a_ten_percent_error():
    """The nine counts of the storage series (test_legacy.py), each with a
    fixed 10 % error component: the earlier fit."""
    fit = fit_decay(STORAGE_T, STORAGE_N, [0.1 * n for n in STORAGE_N])
    assert fit.tau == pytest.approx(2599.7, abs=0.1)
    assert fit.tau_err == pytest.approx(487.2, abs=0.1)
    assert fit.n0 == pytest.approx(1159.8, abs=0.1)
    assert fit.n0_err == pytest.approx(63.8, abs=0.1)
    assert fit.dof == 7
    resid = [(n - fit.n0 * math.exp(-t / fit.tau)) / (0.1 * n)
             for t, n in zip(STORAGE_T, STORAGE_N)]
    assert fit.reduced_chi2 == pytest.approx(sum(r * r for r in resid) / 7)


def test_a_fit_recovers_a_known_decay():
    t = np.array([0, 300, 600, 1200, 2400.0])
    n = 2000 * np.exp(-t / 900)
    fit = fit_decay(t, n, 0.05 * n)
    assert (fit.n0, fit.tau) == (pytest.approx(2000, rel=1e-6),
                                 pytest.approx(900, rel=1e-6))
    assert fit.chi2 == pytest.approx(0, abs=1e-9)


def test_a_fit_needs_errors_and_two_points():
    with pytest.raises(ValueError):
        fit_decay([1, 2], [10, 5], [0, 1])
    with pytest.raises(ValueError):
        fit_decay([1], [10], [1])


def test_two_point_tau():
    """15 and 45 min with the errors typed in earlier (1260 and 385): the
    earlier formula gives 1520.72 +- 709.6 s (the review rounds tau down to
    1520.6); first-order propagation divides that error by ln(N1/N2)."""
    tau, err = two_point_tau(900, 3815, 1260, 2700, 1168, 385, "relative_sum")
    assert tau == pytest.approx(1520.72, abs=0.05)
    assert err == pytest.approx(709.6, abs=0.05)
    tau1, err1 = two_point_tau(900, 3815, 1260, 2700, 1168, 385)
    assert tau1 == tau and err1 == pytest.approx(err / math.log(3815 / 1168))
    with pytest.raises(ValueError):
        two_point_tau(0, 5, 1, 1, 5, 1)


# ── report ────────────────────────────────────────────────────────────────

def test_the_report_files(result, tmp_path):
    result.dataset.errors = ErrorTable((C("counting", "poisson"),))
    fit = fit_decay(STORAGE_T, STORAGE_N, [0.1 * n for n in STORAGE_N])
    files = report.write(str(tmp_path / "out"), [result], [("storage", fit)])
    names = sorted(f.split("\\")[-1].split("/")[-1] for f in files)
    assert names == ["errors.csv", "frames_v.csv", "report.json", "totals.csv"]
    frames = list(csv.DictReader(open(tmp_path / "out" / "frames_v.csv")))
    assert [int(r["excluded"]) for r in frames] == [k == 7 for k in range(10)]
    assert int(frames[3]["nearest: disc_ions"]) == round(F.disc_light(30)
                                                         / F.ION_LIGHT)
    totals = list(csv.DictReader(open(tmp_path / "out" / "totals.csv")))
    mine = [t for t in totals if t["method"] == "nearest"][0]
    assert mine["frames_excluded"] == "7" and mine["storage_time_s"] == "600"
    assert float(mine["error_total"]) == pytest.approx(
        math.sqrt(result.totals["nearest"].count))
    doc = json.load(open(tmp_path / "out" / "report.json"))
    assert doc["datasets"][0]["excluded_frames"] == [7]
    assert doc["fits"][0]["tau_s"] == pytest.approx(2599.7, abs=0.1)
    assert IonParams.from_dict(doc["datasets"][0]["settings"]) == P
