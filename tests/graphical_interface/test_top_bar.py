"""One top bar: program name, File, Help, then the analysis tabs. Every
action is reachable from the menus and every shortcut still works."""
from PySide6 import QtCore, QtWidgets

from dipesh.graphical_interface import widgets

from gui import run_all, settle


def left(widget, win):
    return widget.mapTo(win, QtCore.QPoint(0, 0)).x()


def test_there_is_no_separate_menu_bar(window):
    assert window.menuWidget() is None
    assert window.findChildren(QtWidgets.QMenuBar) == []


def test_file_and_help_sit_on_the_line_of_the_tabs(window):
    bar = window.file_btn.parentWidget()
    first_tab = window.nav.button(0)
    for b in (window.file_btn, window.help_btn):
        assert b.isVisible() and b.parentWidget() is bar
        assert b.geometry().center().y() == first_tab.geometry().center().y()
        assert b.height() == first_tab.height()
    xs = [left(w, window) for w in (window.brand, window.file_btn,
                                    window.help_btn, first_tab,
                                    window.nav.button(5), window.run_btn)]
    assert xs == sorted(xs)
    # same style as the tabs: flat, muted text
    assert (window.file_btn.palette().color(window.file_btn.foregroundRole())
            == first_tab.palette().color(first_tab.foregroundRole()))


def test_the_menus_hold_every_action(window):
    def texts(menu):
        return [a.text() for a in menu.actions() if not a.isSeparator()]
    assert window.file_btn.menu() is window.file_menu
    assert window.help_btn.menu() is window.help_menu
    assert texts(window.file_menu) == ["Add folder…", "Add images…",
                                       "Export…", "Quit"]
    assert texts(window.help_menu) == ["Keyboard shortcuts", "About"]
    keys = {a.text(): a.shortcut().toString() for a in window.file_menu.actions()
            if not a.isSeparator()}
    assert keys == {"Add folder…": "Ctrl+O", "Add images…": "Ctrl+Shift+O",
                    "Export…": "Ctrl+E", "Quit": "Ctrl+Q"}


def recorder(monkeypatch):
    """Stand-ins for the dialogs the actions open; notes which were asked for."""
    seen = []
    monkeypatch.setattr(QtWidgets.QFileDialog, "getExistingDirectory",
                        lambda *a, **k: seen.append("folder") or "")
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileNames",
                        lambda *a, **k: seen.append("images") or ([], ""))
    monkeypatch.setattr(QtWidgets.QMessageBox, "about",
                        lambda *a, **k: seen.append("about"))
    monkeypatch.setattr(QtWidgets.QMessageBox, "information",
                        lambda *a, **k: seen.append("keys"))
    monkeypatch.setattr(widgets.ExportDialog, "exec",
                        lambda self: seen.append("export")
                        or QtWidgets.QDialog.Rejected)
    return seen


def test_every_menu_action_does_its_job(loaded, qtbot, monkeypatch):
    win = loaded
    run_all(win, qtbot)
    seen = recorder(monkeypatch)
    actions = {a.text(): a for menu in (win.file_menu, win.help_menu)
               for a in menu.actions() if not a.isSeparator()}
    for name in ("Add folder…", "Add images…", "Export…",
                 "Keyboard shortcuts", "About"):
        actions[name].trigger()
    assert seen == ["folder", "images", "export", "keys", "about"]
    assert win.isVisible()
    actions["Quit"].trigger()
    assert not win.isVisible()


def test_the_shortcuts_still_trigger(loaded, qtbot, monkeypatch):
    win = loaded
    run_all(win, qtbot)
    seen = recorder(monkeypatch)
    ctrl, shift = QtCore.Qt.ControlModifier, QtCore.Qt.ShiftModifier
    qtbot.keyClick(win, "O", ctrl)
    qtbot.keyClick(win, "O", ctrl | shift)
    qtbot.keyClick(win, "E", ctrl)
    assert seen == ["folder", "images", "export"]
    qtbot.keyClick(win, "3", ctrl)
    assert win.stack.currentIndex() == 2
    first = win.s.current[1]
    qtbot.keyClick(win, QtCore.Qt.Key_PageDown)
    assert win.s.current[1] is not first
    qtbot.keyClick(win, "R", ctrl)
    assert win._thread is not None
    settle(win, qtbot)


def test_ctrl_q_closes_the_window(window, qtbot):
    qtbot.keyClick(window, "Q", QtCore.Qt.ControlModifier)
    assert not window.isVisible()
