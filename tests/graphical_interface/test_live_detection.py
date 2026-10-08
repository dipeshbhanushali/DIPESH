"""The live count follows the sliders and equals detect() on the same frame."""
from dipesh import DetectionParams, detect, load_image

from gui import PBAR_COUNTS, live_result


def direct(win):
    """detect() called directly on the current image with the session's
    settings."""
    return detect(load_image(win.s.current[1].path), win.s.params,
                  photometry=True)


def test_the_live_count_equals_detect_on_the_same_frame(loaded):
    win = loaded
    spots, info = direct(win)
    assert win.s.params == DetectionParams()
    assert win.s.live.n == len(spots) == PBAR_COUNTS[0]   # reference frame 1
    assert win.s.live.spots == spots and win.s.live.info == info
    assert win.detection.count.text() == str(PBAR_COUNTS[0])
    assert win.detection.facts["iso"].text() == str(
        sum(s.is_isolated for s in spots))


def test_moving_a_slider_updates_the_live_result(loaded, qtbot):
    win = loaded
    counts = set()
    for name, value in (("abs_thresh", 200), ("abs_thresh", 60),
                        ("min_dist", 40), ("sum_thresh", 400),
                        ("spot_max_radius", 6)):
        slider = {**win.detection.w, **win.detection.w2}[name]
        with live_result(win, qtbot):
            slider.setValue(value)
        assert getattr(win.s.params, name) == value
        spots, info = direct(win)
        assert win.s.live.spots == spots and win.s.live.info == info
        assert win.detection.count.text() == str(len(spots))
        counts.add(len(spots))
    assert len(counts) > 1                           # the sliders did something


def test_the_slider_and_its_number_box_stay_in_step(window):
    w = window.detection.w["n_sigma"]                # one decimal
    w.slider.setValue(125)
    assert w.box.value() == 12.5 and w.value() == 12.5
    w.box.setValue(7.5)
    assert w.slider.value() == 75
    assert window.s.params.n_sigma == 7.5


def test_reset_defaults_puts_the_settings_back(loaded, qtbot):
    win = loaded
    with live_result(win, qtbot):
        win.detection.w["abs_thresh"].setValue(220)
    with live_result(win, qtbot):
        win.detection.reset()
    assert win.s.params == DetectionParams()
    assert win.detection.w["abs_thresh"].value() == 140
    assert win.s.live.n == PBAR_COUNTS[0]


def test_a_frame_that_cannot_be_read_shows_an_error_not_a_count(
        window, qtbot, tmp_path):
    from dipesh import Item
    bad = tmp_path / "broken.tiff"
    bad.write_bytes(b"not an image")
    ds = window.s.add("broken", [Item(str(bad), 1, str(tmp_path))])
    with live_result(window, qtbot):
        window.sidebar.select(ds, ds.items[0])
    assert not window.s.live.ok
    assert window.detection.count.text() == "!"
