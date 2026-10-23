"""The two looks, Phosphor and Glass: picked in View, kept in the settings,
every page works in both, the data stays, plot areas stay opaque, text keeps
its contrast, and the Windows 11 frame never breaks anything."""
import sys

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from dipesh.graphical_interface import glass, theme
from gui import run_all, settle


def pixel(win, widget, x, y):
    """Colour of the window at a point of widget, as drawn on screen."""
    QtWidgets.QApplication.processEvents()
    img = win.grab().toImage()
    p = widget.mapTo(win, QtCore.QPoint(x, y))
    dpr = img.devicePixelRatio()
    return img.pixelColor(int(p.x() * dpr), int(p.y() * dpr))


def near(a, b, tol=3):
    a, b = QtGui.QColor(a), QtGui.QColor(b)
    return all(abs(x - y) <= tol for x, y in ((a.red(), b.red()),
               (a.green(), b.green()), (a.blue(), b.blue())))


@pytest.fixture
def glassy(window):
    window.set_theme("Glass")
    yield window
    window.set_theme("Phosphor")


def test_phosphor_is_the_default_and_view_offers_both(window):
    assert theme.current() == "Phosphor"
    assert window.theme_actions["Phosphor"].isChecked()
    texts = [a.text() for a in window.view_btn.menu().actions()]
    assert texts == ["Phosphor theme", "Glass theme"]
    assert QtWidgets.QApplication.instance().styleSheet() == \
        theme.stylesheet("Phosphor")


def test_the_choice_is_saved_and_restored(window, qtbot):
    window.theme_actions["Glass"].trigger()
    assert theme.current() == "Glass" and window.backdrop.glass
    assert QtCore.QSettings().value("theme") == "Glass"
    from dipesh.graphical_interface.main_window import MainWindow
    again = MainWindow()                         # a new start of the program
    qtbot.addWidget(again)
    assert again.backdrop.glass and again.theme_actions["Glass"].isChecked()
    again.set_theme("Phosphor")
    assert QtCore.QSettings().value("theme") == "Phosphor"
    window.set_theme("Phosphor")


def test_an_unknown_saved_theme_falls_back_to_phosphor(window):
    window.set_theme("Neon")
    assert theme.current() == "Phosphor" and not window.backdrop.glass


@pytest.mark.parametrize("name", theme.THEMES)
def test_every_page_opens_in_both_themes(loaded, qtbot, name):
    win = loaded
    run_all(win, qtbot)
    win.set_theme(name)
    for k, page in enumerate(win.pages):
        win.show_page(k)
        QtWidgets.QApplication.processEvents()
        assert page.isVisible()
        for j in range(len(getattr(page, "lessons", []))):
            page.show_lesson(j)
            QtWidgets.QApplication.processEvents()
        assert not win.grab().isNull()
    settle(win, qtbot)
    win.set_theme("Phosphor")


def test_switching_keeps_the_data(loaded, qtbot):
    win = loaded
    run_all(win, qtbot)
    win.show_page(2)
    before = ([d.name for d in win.s.datasets],
              [d.colour for d in win.s.datasets],
              {d.name: {k: r.n for k, r in d.results.items()}
               for d in win.s.datasets},
              win.s.current, win.s.params, win.sidebar.summary.text(),
              win.stack.currentIndex())
    for name in ("Glass", "Phosphor", "Glass"):
        win.set_theme(name)
        after = ([d.name for d in win.s.datasets],
                 [d.colour for d in win.s.datasets],
                 {d.name: {k: r.n for k, r in d.results.items()}
                  for d in win.s.datasets},
                 win.s.current, win.s.params, win.sidebar.summary.text(),
                 win.stack.currentIndex())
        assert after == before
    assert not win.s.stale                        # no need to run all again
    win.set_theme("Phosphor")


def test_dataset_colours_are_the_same_in_both_themes():
    assert theme.SERIES == ["#21AC54", "#9A77EC", "#D97100", "#00A3C2",
                            "#E7528C"]


def test_plot_areas_are_opaque_in_glass(loaded, qtbot):
    win = loaded
    run_all(win, qtbot)
    win.set_theme("Glass")
    win.show_page(2)                              # histogram
    plot = win.pages[2].plot
    assert plot.backgroundBrush().color() == QtGui.QColor(theme.PLOT["Glass"])
    vb = plot.getPlotItem().vb
    corner = vb.mapToScene(vb.boundingRect().topLeft()).toPoint()
    at = plot.mapFromScene(corner) + QtCore.QPoint(3, 3)
    # the plot colour exactly: nothing of the backdrop shows through
    assert pixel(win, plot.viewport(), at.x(), at.y()) == \
        QtGui.QColor(theme.PLOT["Glass"])
    win.show_page(0)                              # the image view
    view = win.pages[0].view.ui.graphicsView
    assert pixel(win, view.viewport(), 2, 2) == QtGui.QColor(theme.PLOT["Glass"])
    win.set_theme("Phosphor")
    assert pixel(win, view.viewport(), 2, 2) == QtGui.QColor(theme.PANEL)


def test_panels_are_frosted_and_the_backdrop_shows_between_them(glassy):
    win = glassy
    win.resize(1200, 800)
    QtWidgets.QApplication.processEvents()
    sharp, soft = win.backdrop.images()
    side = win.sidebar
    # an empty spot of the sidebar: the blurred backdrop under the fill
    x, y = side.width() // 2, side.height() - 8
    at = side.mapTo(win.backdrop, QtCore.QPoint(x, y))
    want = glass.over(glass.FILL, soft.pixelColor(at))
    assert near(pixel(win, side, x, y), want)
    # the gap at the window's top left corner is the bare backdrop
    assert near(pixel(win, win.backdrop, 0, 0), sharp.pixelColor(0, 0))


def test_glass_text_meets_wcag_aa():
    """Every text colour reaches 4.5:1 on the lightest a panel can be, and
    on the solid colours of dialogs and pop-ups."""
    worst = glass.brightest_panel()
    for colour in (theme.TEXT, theme.MUTED, theme.PHOSPHOR, theme.AMBER,
                   theme.RED, theme.ISOLATED):
        assert glass.contrast(colour, worst) >= 4.5, colour
        for surface in ("#0D1C18", "#0A1617", theme._G_POP,
                        theme.PLOT["Glass"]):
            assert glass.contrast(colour, surface) >= 4.5, (colour, surface)
    # text on buttons that are filled with the accent
    assert glass.contrast(theme.TUBE, theme.PHOSPHOR) >= 4.5
    assert glass.contrast(theme.TUBE, theme.AMBER) >= 4.5


def test_the_windows_11_frame_does_nothing_where_it_cannot(window,
                                                         monkeypatch):
    assert glass.windows_frame(window, True) is False      # offscreen
    monkeypatch.setattr(QtGui.QGuiApplication, "platformName",
                        staticmethod(lambda: "windows"))
    if sys.platform == "win32":
        monkeypatch.setattr(sys, "getwindowsversion",
                            lambda: type("V", (), {"build": 19045})())
        assert glass.windows_frame(window, True) is False  # Windows 10
        monkeypatch.setattr(sys, "getwindowsversion",
                            lambda: type("V", (), {"build": 26100})())
        # no real window here: Windows refuses, nothing is raised
        assert glass.windows_frame(window, True) in (True, False)
    else:
        assert glass.windows_frame(window, True) is False
