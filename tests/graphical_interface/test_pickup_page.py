"""The pickup page: both scopes of the run, and Apply to all counted runs."""
from PySide6 import QtCore

from dipesh import measure_pickup

from gui import run_all, show


def shown_pickup(win, qtbot):
    page = show(win, "pickup")
    qtbot.waitUntil(lambda: bool(page.traces), timeout=30000)
    return page


def test_the_pickup_page_shows_both_scopes_of_the_run(loaded, qtbot):
    win = loaded
    page = shown_pickup(win, qtbot)
    item = win.s.current[1]
    want, _ = measure_pickup(item.folder, win.s.live.batman, win.s.pickup)
    assert {t.scope for t in page.traces} == {"A", "B"}
    assert [(t.scope, t.channel) for t in page.traces] == [
        (t.scope, t.channel) for t in want]
    assert page.table.rowCount() == 8                # 2 scopes x 4 channels
    assert page.chan.count() == 8 and page.chan.currentText() == "A/chD"
    assert len(page.plot.ci.items) == 2              # one panel per scope
    assert not page.empty.isVisible()

    by_key = {t.key: t for t in page.traces}
    assert by_key["AD"].pulse["found"] and by_key["BD"].pulse["found"]
    assert by_key["BD"].delay_us == 5000.0           # PT_TrapTime
    row = [t.key for t in page.traces].index("AD")
    assert page.table.item(row, 2).text() == "found"
    assert page.table.item(row, 3).text() == f"{by_key['AD'].pulse['peak_time_us']:.3f}"
    assert "26.92" in page.rf_note.text() and "53.84" in page.rf_note.text()


def test_one_channel_view_draws_the_chosen_trace(loaded, qtbot):
    page = shown_pickup(loaded, qtbot)
    page.mode.setCurrentIndex(1)
    assert len(page.plot.ci.items) == 1
    page.chan.setCurrentText("B/chD")
    assert len(page.plot.ci.items) == 1


def test_switching_the_notch_off_loses_the_pulse(loaded, qtbot):
    page = shown_pickup(loaded, qtbot)
    page.traces = []
    page.rf_on.setChecked(False)
    qtbot.waitUntil(lambda: bool(page.traces), timeout=30000)
    assert not loaded.s.pickup.rf_enabled
    d = next(t for t in page.traces if t.key == "AD")
    assert not d.rf["applied"] and not d.pulse["found"]


def test_a_run_without_picoscope_files_says_so(loaded, qtbot):
    win = loaded
    page = shown_pickup(win, qtbot)
    ds = win.s.datasets[1]                           # background: no scopes
    win.sidebar.select(ds, ds.items[0])
    qtbot.waitUntil(lambda: not page.traces, timeout=30000)
    assert page.empty.isVisible() and page.table.rowCount() == 0


def test_apply_to_all_counted_runs_fills_the_pickup_columns(loaded, qtbot):
    win = loaded
    run_all(win, qtbot)
    page = shown_pickup(win, qtbot)
    pbar = win.s.datasets[0]
    for r in pbar.done():
        r.pickup = {}
    qtbot.mouseClick(page.apply_all, QtCore.Qt.LeftButton)
    for r in pbar.done():
        _, want = measure_pickup(r.item.folder, r.batman, win.s.pickup)
        assert r.pickup == want and len(want) == 2 * (4 * 4 + 1)
        assert r.pickup["pickup_A_chD_area"] > 0
    plots = show(win, "plots")
    assert plots.y.findData("pickup_A_chD_area") >= 0
    assert plots.y.findData("pickup_B_delay_us") < 0     # delays are not offered


def test_find_in_files_reads_the_scope_tags_from_the_filenames(loaded, qtbot):
    win = loaded
    page = shown_pickup(win, qtbot)
    page._discover()
    tags = [s.file_tag for s in win.s.pickup.scopes]
    assert tags == ["PbarExtractionRange10_20260806_MCP1",
                    "PbarExtraction_2_Range10_20260806_MCP1"]
    assert page.scopes.rowCount() == 2
