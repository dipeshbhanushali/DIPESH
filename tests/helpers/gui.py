"""Small helpers for the GUI tests: waiting for background work."""
import json
import os

from PySide6 import QtCore, QtWidgets

_REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "reference", "golden.json")
with open(_REF) as _f:
    _GOLDEN = json.load(_f)["frames"]
# counts of reference frames 1, 2, 3: the three pbar runs of the test data
PBAR_COUNTS = [_GOLDEN[f"frame_{k}.tiff"]["count"] for k in (1, 2, 3)]


def settle(win, qtbot):
    """Wait until Run all / Export and every pooled job have finished."""
    qtbot.waitUntil(lambda: win._thread is None, timeout=60000)
    QtCore.QThreadPool.globalInstance().waitForDone(30000)
    QtWidgets.QApplication.processEvents()


def live_result(win, qtbot):
    """`with live_result(win, qtbot): change something` waits for the live
    detection that the change starts (only the newest result is announced)."""
    return qtbot.waitSignal(win.s.liveChanged, timeout=30000)


def run_all(win, qtbot):
    win.run_all()
    settle(win, qtbot)


def page(win, title):
    return next(p for p in win.pages if p.title == title)


def show(win, title):
    """Switch to a page by name and let it draw."""
    k = next(i for i, p in enumerate(win.pages) if p.title == title)
    win.show_page(k)
    QtWidgets.QApplication.processEvents()
    return win.pages[k]
