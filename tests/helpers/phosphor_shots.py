"""
Pictures of every page in the Phosphor theme, to prove that work on the
Glass theme leaves Phosphor pixel for pixel as it was.

    py tests/helpers/phosphor_shots.py      rewrite the reference pictures

The reference pictures in tests/graphical_interface/phosphor_reference/ were
made from the code before Glass "Strong" existed (commit 2469ef1). Rewrite
them only on purpose, when the Phosphor look itself is meant to change.
They are drawn offscreen with no fonts, as the tests are, so the same Qt
version draws the same pixels; versions.json says which versions made them.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "..", "graphical_interface", "phosphor_reference")
SIZE = (1480, 920)


def versions():
    import PySide6
    import pyqtgraph
    from PySide6 import QtCore
    return {"qt": QtCore.qVersion(), "pyside6": PySide6.__version__,
            "pyqtgraph": pyqtgraph.__version__, "platform": sys.platform}


def idle(win, seconds=60):
    """Wait until Run all, live detection and drawing have finished."""
    from PySide6 import QtCore, QtWidgets
    end = time.time() + seconds
    pool = QtCore.QThreadPool.globalInstance()
    while time.time() < end:
        QtWidgets.QApplication.processEvents()
        if win._thread is None and pool.activeThreadCount() == 0:
            break
        time.sleep(0.01)
    pool.waitForDone(30000)
    for _ in range(3):
        QtWidgets.QApplication.processEvents()


def fill(win, data_root):
    """The three test datasets added, first run selected, Run all done."""
    for name in ("pbar_scan", "background", "ions"):
        win.sidebar.add_paths([os.path.join(data_root, name)])
    idle(win)
    win.run_all()
    idle(win)


def shots(win):
    """{name: QImage} of every page and every learn lesson. The console is
    emptied first: it holds clock times and run times."""
    from PySide6 import QtWidgets
    QtWidgets.QApplication.processEvents()       # minimum sizes up to date
    win.centralWidget().layout().activate()
    win.resize(*SIZE)
    win.console.clear()
    out = {}
    for k, page in enumerate(win.pages):
        win.show_page(k)
        idle(win)
        for j in range(len(getattr(page, "lessons", []))):
            page.show_lesson(j)
            idle(win)
            out[f"{k + 1}_learn_{j + 1}"] = win.grab().toImage()
        if not hasattr(page, "lessons"):
            out[f"{k + 1}_{page.title}"] = win.grab().toImage()
    win.show_page(0)
    QtWidgets.QApplication.processEvents()
    return out


def main():
    import tempfile
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.path.insert(0, os.path.join(HERE, "..", ".."))
    sys.path.insert(0, HERE)
    from PySide6 import QtCore, QtWidgets
    tmp = tempfile.mkdtemp(prefix="dipesh_ref_")
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(QtCore.QSettings.IniFormat,
                             QtCore.QSettings.UserScope, tmp)
    app = QtWidgets.QApplication([])
    app.setStyle("Fusion")
    import make_testdata
    from dipesh.graphical_interface.main_window import MainWindow
    from dipesh.graphical_interface.theme import setup_pyqtgraph, stylesheet
    app.setStyleSheet(stylesheet())
    setup_pyqtgraph()
    data = make_testdata.build(os.path.join(tmp, "data"), n_pbar=3,
                               n_synthetic=2, n_loose=2)
    win = MainWindow()
    win.show()
    fill(win, data)
    os.makedirs(REF, exist_ok=True)
    for name, img in shots(win).items():
        img.save(os.path.join(REF, f"{name}.png"))
        print("wrote", name)
    with open(os.path.join(REF, "versions.json"), "w") as f:
        json.dump(versions(), f, indent=1)
    win.close()


if __name__ == "__main__":
    main()
