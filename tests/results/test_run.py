"""analyse() and RunResult."""
import math

from dipesh import (DetectionParams, Item, RunResult,
                                 RUN_METRICS, analyse, detect, load_image,
                                 scan)


def test_analyse_reports_a_bad_image_instead_of_raising(tmp_path):
    r = analyse(Item(str(tmp_path / "nope.tiff"), 1, str(tmp_path)),
                DetectionParams())
    assert not r.ok and r.n == 0


def test_analyse_is_detect_with_photometry_plus_the_batman(tmp_path,
                                                           run_folder):
    d, pts = run_folder(tmp_path, 7, n=4, batman={"ExtLine_MCP": 1650})
    item = scan(str(tmp_path))[0]
    r = analyse(item, DetectionParams())
    spots, info = detect(load_image(item.path), DetectionParams(),
                         photometry=True)
    assert r.ok and r.n == len(pts) == len(spots)
    assert r.spots == spots and r.info == info
    assert r.batman == {"ExtLine_MCP": 1650.0}


def test_every_run_metric_is_a_number(tmp_path, run_folder):
    run_folder(tmp_path, 7, n=4, batman={"ExtLine_MCP": 1650})
    r = analyse(scan(str(tmp_path))[0], DetectionParams())
    for name in RUN_METRICS:
        assert math.isfinite(r.metric(name)), name
    assert r.metric("pbar_count") == 4.0
    assert r.metric("run_number") == 7.0
    assert r.metric("n_isolated") == 4.0


def test_metric_falls_back_to_pickup_then_batman_then_nan(tmp_path):
    r = RunResult(Item("x.tiff", 3, str(tmp_path)),
                  batman={"PT_TrapTime": 5000.0, "both": 1.0},
                  pickup={"pickup_A_chD_area": 0.25, "both": 2.0,
                          "pickup_A_chD_peak_time_us": ""})
    assert r.metric("pickup_A_chD_area") == 0.25
    assert r.metric("PT_TrapTime") == 5000.0
    assert r.metric("both") == 2.0                    # pickup wins
    assert math.isnan(r.metric("pickup_A_chD_peak_time_us"))   # no pulse
    assert math.isnan(r.metric("no_such_thing"))
    assert math.isnan(r.metric("integrated_lum"))    # no image analysed
