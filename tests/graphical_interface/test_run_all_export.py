"""Run all and Export: the session holds what analyse() gives, and the files
on disk agree with the session."""
import csv
import json

from PySide6 import QtCore, QtWidgets

from dipesh import DetectionParams, analyse
from dipesh.graphical_interface import widgets

from gui import PBAR_COUNTS, live_result, run_all, settle


def test_run_all_gives_the_same_counts_as_analyse(loaded, qtbot):
    win = loaded
    qtbot.mouseClick(win.run_btn, QtCore.Qt.LeftButton)
    assert not win.run_btn.isEnabled()               # busy
    settle(win, qtbot)
    for ds in win.s.datasets:
        assert len(ds.done()) == len(ds.items)
        for item in ds.items:
            want = analyse(item, DetectionParams())
            got = ds.result(item)
            assert got.n == want.n and got.spots == want.spots
            assert got.info == want.info and got.batman == want.batman
    assert [r.n for r in win.s.datasets[0].done()] == PBAR_COUNTS
    assert not win.progress.isVisible()
    assert win.sidebar.summary.text() == "7 images, 7 counted"
    assert win.sidebar.tree.topLevelItem(0).text(1) == str(sum(PBAR_COUNTS))
    assert win.export_btn.isEnabled()


def test_run_all_also_measures_the_pickup_of_each_run(loaded, qtbot):
    win = loaded
    run_all(win, qtbot)
    pbar, background = win.s.datasets[0], win.s.datasets[1]
    for r in pbar.done():
        assert r.pickup["pickup_B_delay_us"] == 5000.0
        assert r.pickup["pickup_A_chD_amplitude_V"] > 0.004
    assert all(r.pickup == {} for r in background.done())


def test_the_button_reads_run_all_again_after_the_settings_change(loaded,
                                                                  qtbot):
    win = loaded
    assert win.run_btn.text() == "Run all"
    run_all(win, qtbot)
    assert win.run_btn.text() == "Run all" and not win.s.stale
    with live_result(win, qtbot):
        win.detection.w["abs_thresh"].setValue(180)
    assert win.s.stale
    assert win.run_btn.text() == "Run all again"
    assert win.run_btn.objectName() == "stale"
    run_all(win, qtbot)
    assert win.run_btn.text() == "Run all" and not win.s.stale
    assert win.s.results_params.abs_thresh == 180


def test_ctrl_r_runs_all(loaded, qtbot):
    win = loaded
    qtbot.keyClick(win, "R", QtCore.Qt.ControlModifier)
    assert win._thread is not None
    settle(win, qtbot)
    assert len(win.s.datasets[0].done()) == 3


def patch_dialog(monkeypatch, out, marked=True, master=None, accept=True):
    """Stand in for the export dialog: no modal window opens."""
    monkeypatch.setattr(widgets.ExportDialog, "exec", lambda self: (
        QtWidgets.QDialog.Accepted if accept else QtWidgets.QDialog.Rejected))
    monkeypatch.setattr(widgets.ExportDialog, "values",
                        lambda self: (str(out), marked, master, False))


def test_export_writes_files_that_agree_with_the_session(loaded, qtbot,
                                                         tmp_path, monkeypatch):
    win = loaded
    run_all(win, qtbot)
    out = tmp_path / "out"
    # marked images are left out here to keep the test quick (0.8 s per
    # frame); test_threads.py exports them
    patch_dialog(monkeypatch, out, marked=False)
    qtbot.mouseClick(win.export_btn, QtCore.Qt.LeftButton)
    settle(win, qtbot)

    rows = list(csv.DictReader(open(out / "counts.csv")))
    want = [(d.name, r) for d in win.s.datasets for r in d.done()]
    assert len(rows) == len(want) == 7
    for row, (name, r) in zip(rows, want):
        assert row["dataset"] == name
        assert int(row["run_number"]) == r.item.run_number
        assert int(row["pbar_count"]) == r.n
        assert row["pbar_count_lum"] == f"{r.info.pbar_count_lum:.2f}"
    assert rows[0]["pickup_A_chD_area"] != "" and rows[0]["PT_TrapTime"] == "5000.0"

    spots = list(csv.DictReader(open(out / "spots.csv")))
    assert len(spots) == sum(r.n for _, r in want)
    params = json.load(open(out / "params.json"))
    assert params["params"] == json.loads(json.dumps(
        win.s.results_params.to_dict()))
    assert params["datasets"] == {"pbar_scan": 3, "background": 2, "ions": 2}


def test_export_uses_the_counted_results_not_the_current_sliders(
        loaded, qtbot, tmp_path, monkeypatch):
    win = loaded
    run_all(win, qtbot)
    with live_result(win, qtbot):
        win.detection.w["abs_thresh"].setValue(250)
    out = tmp_path / "out"
    patch_dialog(monkeypatch, out, marked=False)
    win.export()
    settle(win, qtbot)
    assert json.load(open(out / "params.json"))["params"]["abs_thresh"] == 140.0
    rows = list(csv.DictReader(open(out / "counts.csv")))
    assert [int(r["pbar_count"]) for r in rows[:3]] == PBAR_COUNTS


def test_export_appends_to_the_master_archive(loaded, qtbot, tmp_path,
                                              monkeypatch):
    win = loaded
    run_all(win, qtbot)
    patch_dialog(monkeypatch, tmp_path / "out", marked=False,
                 master=str(tmp_path / "master"))
    win.export()
    settle(win, qtbot)
    rows = list(csv.DictReader(open(tmp_path / "master" / "master_runs.csv")))
    assert len(rows) == 7


def test_a_cancelled_export_writes_nothing(loaded, qtbot, tmp_path,
                                           monkeypatch):
    win = loaded
    run_all(win, qtbot)
    patch_dialog(monkeypatch, tmp_path / "out", accept=False)
    win.export()
    assert win._thread is None and not (tmp_path / "out").exists()


def test_export_before_run_all_does_nothing(loaded, tmp_path, monkeypatch):
    win = loaded
    patch_dialog(monkeypatch, tmp_path / "out")
    win.export()
    assert win._thread is None and not (tmp_path / "out").exists()


def test_the_export_dialog_remembers_its_folder(window, qtbot, tmp_path):
    dlg = widgets.ExportDialog(window, window.s)
    qtbot.addWidget(dlg)
    dlg.out.setText(str(tmp_path / "there"))
    dlg.marked.setChecked(False)
    dlg._accept()
    assert dlg.values() == (str(tmp_path / "there"), False, None, False)
    again = widgets.ExportDialog(window, window.s)
    qtbot.addWidget(again)
    assert again.out.text() == str(tmp_path / "there")
    assert not again.marked.isChecked()
