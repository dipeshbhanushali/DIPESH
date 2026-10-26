"""
How small the window can be, page by page, in every look, with the
settings panel open and folded. Run by test_small_screen.py in a process of
its own, with the system's fonts (the other GUI tests draw without fonts,
which makes text wider than on a real screen).

    py tests/helpers/fit_check.py      -> JSON on stdout
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

# a 1536 x 864 screen (1920 x 1080 at 125 %), less the taskbar (48) and the
# title bar (30): the room a maximised window has
ROOM = (1536, 786)


def main():
    from PySide6 import QtCore, QtWidgets
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(QtCore.QSettings.IniFormat,
                             QtCore.QSettings.UserScope, tempfile.mkdtemp())
    app = QtWidgets.QApplication([])
    app.setStyle("Fusion")
    import make_testdata
    import phosphor_shots
    from dipesh.graphical_interface.main_window import MainWindow
    from dipesh.graphical_interface.theme import setup_pyqtgraph, stylesheet
    app.setStyleSheet(stylesheet())
    setup_pyqtgraph()
    win = MainWindow()
    win.show()
    win.set_animation(False, save=False)
    data = make_testdata.build(os.path.join(tempfile.mkdtemp(), "d"),
                               n_pbar=3, n_synthetic=2, n_loose=2)
    phosphor_shots.fill(win, data)
    out = []
    for look, level in (("Phosphor", "Strong"), ("Glass", "Subtle"),
                        ("Glass", "Strong")):
        win.set_glass_intensity(level, save=False)
        win.set_theme(look, save=False)
        for panel in (True, False):
            win.set_settings_panel(panel, save=False)
            for k, page in enumerate(win.pages):
                win.show_page(k)
                app.processEvents()
                win.centralWidget().layout().activate()
                m = win.minimumSizeHint()
                win.resize(*ROOM)
                app.processEvents()
                out.append({"look": f"{look} {level}", "panel": panel,
                            "page": page.title, "min": [m.width(), m.height()],
                            "size": [win.width(), win.height()],
                            "panel_width": (page.side if hasattr(page, "side")
                                            else win.right).width()})
    win.set_theme("Phosphor", save=False)
    win.close()
    print(json.dumps({"room": ROOM, "fonts": os.environ.get("QT_QPA_FONTDIR"),
                      "pages": out}))


if __name__ == "__main__":
    main()
