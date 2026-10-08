"""DIPESH - the desktop app. `dipesh` and `python -m dipesh`
both start here.

    dipesh                 the program
    dipesh --selftest      start, show the window, close after 5 s and
                             return 0: a quick check that an install works
    dipesh --selftest=1    the same with another number of seconds
"""

import sys

from PySide6 import QtCore, QtWidgets

from .main_window import MainWindow
from .theme import APP_NAME, setup_pyqtgraph, stylesheet


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    selftest = None
    for a in [a for a in argv if a.startswith("--selftest")]:
        argv.remove(a)
        selftest = float(a.partition("=")[2] or 5)

    QtCore.QCoreApplication.setOrganizationName("DIPESH")
    QtCore.QCoreApplication.setApplicationName(APP_NAME)
    app = QtWidgets.QApplication(argv)
    app.setStyle("Fusion")
    app.setStyleSheet(stylesheet())
    setup_pyqtgraph()
    win = MainWindow()
    win.show()
    if selftest is not None:
        QtCore.QTimer.singleShot(int(selftest * 1000), win.close)
    return app.exec()
