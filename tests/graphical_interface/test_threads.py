"""
Run all and Export report their progress on the GUI thread.

An early build connected the workers' progress signal to a lambda; PySide6 called it in
the worker thread, which then touched the progress bar and crashed the app now
and then ("QBasicTimer::stop: Failed. Possibly trying to stop from a different
thread").
"""
from PySide6 import QtCore, QtWidgets

from dipesh import DetectionParams, analyse, scan
from dipesh.graphical_interface import main_window as gui

REPEATS = 5              # a race does not show every time


class ThreadLog:
    """Notes, for every progress-bar update, whether it ran on the GUI thread.

    The slots themselves are left alone and the bar's setValue is wrapped
    instead: a slot overridden in a Python subclass is called by PySide6
    (6.11) directly in the emitting thread, queued connection or not, so a
    recording subclass of MainWindow would create the very bug it looks for.
    """

    def __init__(self, bar):
        # held for the whole test: PySide hands out a new Python object for
        # the same QThread once the old one is collected, and `is` needs one
        self.gui_thread = QtWidgets.QApplication.instance().thread()
        self.calls = {"run": [], "export": []}
        self.phase = "run"
        real = bar.setValue

        def set_value(v):
            self.calls[self.phase].append(self.on_gui_thread())
            real(v)
        bar.setValue = set_value

    def on_gui_thread(self):
        return QtCore.QThread.currentThread() is self.gui_thread


def test_run_all_and_export_progress_arrive_on_the_gui_thread(
        window, qtbot, tmp_path, monkeypatch, qt_messages, run_folder):
    runs = tmp_path / "runs"
    runs.mkdir()
    for k in range(3):
        run_folder(runs, 100 + k, n=3 + k, seed=k, size=128)
    items = scan(str(runs))
    want = {it.path: analyse(it, DetectionParams()) for it in items}

    win = window
    win.s.add("runs", items)
    log = ThreadLog(win.progress)
    assert log.on_gui_thread()

    out = tmp_path / "out"
    monkeypatch.setattr(gui.ExportDialog, "exec",
                        lambda self: QtWidgets.QDialog.Accepted)
    monkeypatch.setattr(gui.ExportDialog, "values",
                        lambda self: (str(out), True, None, False))

    for _ in range(REPEATS):
        log.phase = "run"
        win.run_all()
        qtbot.waitUntil(lambda: win._thread is None, timeout=30000)
        got = win.s.datasets[0].results
        assert set(got) == set(want)
        for path, r in got.items():
            assert r.ok and r.n == want[path].n
            assert ([s.as_tuple() for s in r.spots]
                    == [s.as_tuple() for s in want[path].spots])

        log.phase = "export"
        win.export()
        qtbot.waitUntil(lambda: win._thread is None, timeout=30000)
        assert (out / "counts.csv").exists()
        assert len(list((out / "marked").iterdir())) == len(items)

    # run_all itself resets the bar once (setValue(0)) before the worker starts
    assert len(log.calls["run"]) == REPEATS * (len(items) + 1)
    assert len(log.calls["export"]) == REPEATS * len(items)
    assert all(log.calls["run"]) and all(log.calls["export"])
    # the qt_messages fixture fails the test on "different thread" or
    # "QBackingStore" in anything Qt printed
