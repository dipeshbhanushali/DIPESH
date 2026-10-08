"""
Fixtures for the GUI tests. They run without a screen: the offscreen platform
is chosen here, before Qt starts.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest                                                      # noqa: E402
from PySide6 import QtCore, QtWidgets                              # noqa: E402

import make_testdata                                               # noqa: E402
from gui import live_result, settle                                # noqa: E402

BAD_MESSAGES = ("different thread", "QBackingStore",
                "Destroyed while thread is still running")


@pytest.fixture(scope="session")
def data_root(tmp_path_factory):
    """The folder written by tests/helpers/make_testdata.py, kept small:
    3 pbar runs on reference frames (two scopes each), 2 background and 2 ion runs.
    Shared by the session; tests only read it."""
    return make_testdata.build(str(tmp_path_factory.mktemp("data")),
                               n_pbar=3, n_synthetic=2, n_loose=2)


@pytest.fixture(scope="session")
def styled_app(qapp):
    """The application with the program's style sheet, as main() sets it."""
    from dipesh.graphical_interface.theme import (
        setup_pyqtgraph, stylesheet)
    qapp.setStyle("Fusion")
    qapp.setStyleSheet(stylesheet())
    setup_pyqtgraph()
    return qapp


@pytest.fixture
def qt_messages():
    """Every message Qt prints during the test; the test fails afterwards on
    a thread or backing-store complaint."""
    seen = []
    old = QtCore.qInstallMessageHandler(lambda mode, ctx, msg: seen.append(msg))
    yield seen
    QtCore.qInstallMessageHandler(old)
    bad = [m for m in seen if any(b in m for b in BAD_MESSAGES)]
    assert not bad, bad


@pytest.fixture
def window(styled_app, qtbot, qt_messages, monkeypatch, tmp_path):
    """The main window, shown, with no data. Every thread is finished before
    the window is closed. Settings go to a file in tmp_path, not the registry."""
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(QtCore.QSettings.IniFormat,
                             QtCore.QSettings.UserScope, str(tmp_path / "qs"))
    from dipesh.graphical_interface.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    yield win
    settle(win, qtbot)
    win.close()
    QtWidgets.QApplication.processEvents()


@pytest.fixture
def loaded(window, qtbot, data_root):
    """The window with the three test datasets added the way the Add folder
    dialog does it, and the first pbar run selected and detected."""
    with live_result(window, qtbot):
        for name in ("pbar_scan", "background", "ions"):
            window.sidebar.add_paths([os.path.join(data_root, name)])
    return window
