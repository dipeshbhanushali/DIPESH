"""
Screenshots of every page in both themes, for checking the look by eye:

    py docs/make_screenshots.py              -> docs/screenshots/v2/*.png
    py docs/make_screenshots.py --out DIR    -> somewhere else

The window is filled with the test data of tests/helpers/make_testdata.py
(written to a temporary folder) and Run all is done first, so every page has
something to show. Your own settings are not touched: the program's settings
go to the temporary folder too. The window shows on the screen for about
half a minute while the pictures are taken.

Files: <theme>_<k>_<page>.png for each page, <theme>_learn_<k>_<lesson>.png
for each lesson of the learn page, <theme>_dialog_export.png.
"""

import argparse
import os
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "helpers"))

from PySide6 import QtCore, QtWidgets                              # noqa: E402

SIZE = (1480, 920)


def wait(win, seconds=60):
    """Let Run all, live detection and drawing finish."""
    app = QtWidgets.QApplication.instance()
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        if win._thread is None and \
                QtCore.QThreadPool.globalInstance().activeThreadCount() == 0:
            break
        time.sleep(0.02)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=os.path.join(HERE, "screenshots", "v2"))
    ap.add_argument("--offscreen", action="store_true",
                    help="no window on the screen (plot text is drawn less "
                         "well: use it only where there is no display)")
    args = ap.parse_args(argv)
    if args.offscreen:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        # the offscreen platform finds no fonts of its own: give it the system's
        if sys.platform == "win32":
            os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(
                os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    tmp = tempfile.mkdtemp(prefix="dipesh_shots_")
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(QtCore.QSettings.IniFormat,
                             QtCore.QSettings.UserScope, tmp)
    QtCore.QCoreApplication.setOrganizationName("DIPESH")
    QtCore.QCoreApplication.setApplicationName("DIPESH")
    app = QtWidgets.QApplication(sys.argv[:1])
    app.setStyle("Fusion")

    import make_testdata
    from dipesh.graphical_interface import theme
    from dipesh.graphical_interface.main_window import MainWindow
    from dipesh.graphical_interface.widgets import ExportDialog

    app.setStyleSheet(theme.stylesheet())
    theme.setup_pyqtgraph()
    data = make_testdata.build(os.path.join(tmp, "data"), n_pbar=6,
                               n_synthetic=5, n_loose=3)
    win = MainWindow()
    win.resize(*SIZE)
    win.show()
    for name in ("pbar_scan", "background", "ions"):
        win.sidebar.add_paths([os.path.join(data, name)])
    wait(win)
    win.run_all()
    wait(win)

    written = []
    for name in theme.THEMES:
        win.set_theme(name)
        wait(win)
        for k, page in enumerate(win.pages):
            win.show_page(k)
            wait(win)
            if hasattr(page, "lessons"):
                for j, lesson in enumerate(page.lessons):
                    page.show_lesson(j)
                    wait(win)
                    title = getattr(lesson, "title", str(j))
                    path = os.path.join(out, f"{slug(name)}_learn_{j + 1}_"
                                             f"{slug(title)}.png")
                    win.grab().save(path)
                    written.append(path)
                continue
            path = os.path.join(out, f"{slug(name)}_{k + 1}_{page.title}.png")
            win.grab().save(path)
            written.append(path)
        dlg = ExportDialog(win, win.s)
        dlg.show()
        wait(win)
        path = os.path.join(out, f"{slug(name)}_dialog_export.png")
        dlg.grab().save(path)
        written.append(path)
        dlg.close()
    win.set_theme("Phosphor")
    win.close()
    for p in written:
        print("wrote", os.path.relpath(p, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
