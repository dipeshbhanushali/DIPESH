"""The looks, Phosphor and Glass (Subtle and Strong): picked in View, kept in
the settings, every page works in each, the data stays, plot areas stay
opaque, text keeps its contrast, the Strong glass is cached and its drift
stays cheap and polite, and the Windows 11 frame never breaks anything."""
import dataclasses
import sys

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from dipesh.graphical_interface import glass, theme
from gui import run_all, settle

LOOKS = [("Phosphor", "Strong"), ("Glass", "Subtle"), ("Glass", "Strong")]


def pixel(win, widget, x, y, img=None):
    """Colour of the window at a point of widget, as drawn on screen (from
    img, a picture of the window, when given: one picture, many points)."""
    if img is None:
        QtWidgets.QApplication.processEvents()
        img = win.grab().toImage()
    p = widget.mapTo(win, QtCore.QPoint(x, y))
    dpr = img.devicePixelRatio()
    return img.pixelColor(int(p.x() * dpr), int(p.y() * dpr))


def picture(win):
    QtWidgets.QApplication.processEvents()
    return win.grab().toImage()


def near(a, b, tol=3):
    a, b = QtGui.QColor(a), QtGui.QColor(b)
    return all(abs(x - y) <= tol for x, y in ((a.red(), b.red()),
               (a.green(), b.green()), (a.blue(), b.blue())))


def look(win, name, level):
    win.set_glass_intensity(level, save=False)
    win.set_theme(name, save=False)


@pytest.fixture
def strong(window):
    """The window in Strong glass, not drifting. (The next window starts in
    its saved look again, so no need to switch back: each switch restyles
    every widget and takes about 2 s.)"""
    window.set_animation(False, save=False)
    look(window, "Glass", "Strong")
    return window


# ── the View menu and the settings ─────────────────────────────────────────

def test_phosphor_is_the_default_and_view_offers_every_choice(window):
    assert theme.current() == "Phosphor"
    assert window.theme_actions["Phosphor"].isChecked()
    texts = [a.text() for a in window.view_menu.actions()
             if not a.isSeparator()]
    assert texts == ["Phosphor theme", "Glass theme", "Glass intensity",
                     "Animate background", "Settings panel"]
    assert [a.text() for a in window.intensity_menu.actions()] == \
        ["Subtle", "Strong"]
    assert window.intensity_actions["Strong"].isChecked()   # Glass default
    assert window.animate_action.isChecked()
    assert QtWidgets.QApplication.instance().styleSheet() == \
        theme.stylesheet("Phosphor")


def test_the_choices_are_saved_and_restored(window, qtbot):
    window.theme_actions["Glass"].trigger()
    window.intensity_actions["Subtle"].trigger()
    window.animate_action.trigger()                          # off
    st = QtCore.QSettings()
    assert (st.value("theme"), st.value("glass_intensity")) == \
        ("Glass", "Subtle")
    assert st.value("animate_background", type=bool) is False
    from dipesh.graphical_interface.main_window import MainWindow
    again = MainWindow()                         # a new start of the program
    qtbot.addWidget(again)
    assert again.backdrop.glass and again.backdrop.intensity == "Subtle"
    assert again.intensity_actions["Subtle"].isChecked()
    assert not again.animate_action.isChecked()
    again.set_theme("Phosphor")
    again.close()
    again.deleteLater()


def test_unknown_saved_choices_fall_back_to_the_defaults(window):
    window.set_glass_intensity("Loud")
    window.set_theme("Neon")
    assert theme.current() == "Phosphor" and not window.backdrop.glass
    assert window.glass_intensity == "Strong"


# ── every page, the data, opaque plots ────────────────────────────────────

@pytest.mark.parametrize("name,level", LOOKS[1:])
def test_every_page_opens_in_every_glass_look(loaded, qtbot, name, level):
    """(Every Phosphor page: test_phosphor_unchanged.py.)"""
    win = loaded
    run_all(win, qtbot)
    look(win, name, level)
    for k, page in enumerate(win.pages):
        win.show_page(k)
        QtWidgets.QApplication.processEvents()
        assert page.isVisible()
        for j in range(len(getattr(page, "lessons", []))):
            page.show_lesson(j)
            QtWidgets.QApplication.processEvents()
        assert not win.grab().isNull()
    settle(win, qtbot)


def test_switching_keeps_the_data(loaded, qtbot):
    win = loaded
    run_all(win, qtbot)
    win.show_page(2)

    def state():
        return ([d.name for d in win.s.datasets],
                [d.colour for d in win.s.datasets],
                {d.name: {k: r.n for k, r in d.results.items()}
                 for d in win.s.datasets},
                win.s.current, win.s.params, win.sidebar.summary.text(),
                win.stack.currentIndex(), list(win.console.lines))
    before = state()
    for name, level in LOOKS[1:] + LOOKS[:1]:
        look(win, name, level)
        assert state() == before
    assert not win.s.stale                        # no need to run all again


def test_dataset_colours_are_the_same_in_every_look():
    assert theme.SERIES == ["#21AC54", "#9A77EC", "#D97100", "#00A3C2",
                            "#E7528C"]


@pytest.mark.parametrize("level", glass.INTENSITIES)
def test_plot_areas_are_opaque_in_glass(loaded, qtbot, level):
    win = loaded
    run_all(win, qtbot)
    win.set_animation(False, save=False)
    look(win, "Glass", level)
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
    look(win, "Phosphor", "Strong")
    assert pixel(win, view.viewport(), 2, 2) == QtGui.QColor(theme.PANEL)


def test_strong_plots_sit_in_a_glass_frame(loaded, qtbot):
    win = loaded
    win.set_animation(False, save=False)
    look(win, "Glass", "Strong")
    win.show_page(2)
    plot = win.pages[2].plot
    frames = glass.plot_frames(win.stack)(win.stack)
    assert plot in frames
    # just outside the plot: the frame's light edge, lighter than the panel
    # a little further out
    edge = pixel(win, plot, plot.width() // 2, -glass.S_FRAME_PAD)
    out = pixel(win, plot, plot.width() // 2, -glass.S_FRAME_PAD - 4)
    assert glass.luminance(edge) > glass.luminance(out)


# ── what the glass looks like ─────────────────────────────────────────────

def test_subtle_panels_are_frosted_and_the_backdrop_shows_between_them(
        window):
    win = window
    look(win, "Glass", "Subtle")
    win.resize(1200, 800)
    QtWidgets.QApplication.processEvents()
    sharp, soft = win.backdrop.images()
    side = win.sidebar
    x, y = side.width() // 2, side.height() - 8
    at = side.mapTo(win.backdrop, QtCore.QPoint(x, y))
    want = glass.over(glass.FILL, soft.pixelColor(at))
    assert near(pixel(win, side, x, y), want)
    assert near(pixel(win, win.backdrop, 0, 0), sharp.pixelColor(0, 0))


def test_strong_panels_are_clear_glass_over_a_blur_with_a_shadow(strong):
    win = strong
    win.resize(1200, 800)
    QtWidgets.QApplication.processEvents()
    sharp, soft = win.backdrop.images()
    side = win.sidebar
    # inside, below the sheen: blur, darkened, plus the white fill
    x, y = side.width() // 2, side.height() - 20
    at = side.mapTo(win.backdrop, QtCore.QPoint(x, y))
    want = glass.strong_panel(soft.pixelColor(at))
    assert near(pixel(win, side, x, y), want, tol=4)
    # the blur is strong: the backdrop's graticule does not show through
    img = picture(win)
    row = [pixel(win, side, xx, y, img) for xx in range(20, side.width() - 20)]
    assert max(glass.luminance(c) for c in row) - \
        min(glass.luminance(c) for c in row) < 0.01
    # the corner is round: the backdrop shows at the panel's corner
    c = side.mapTo(win.backdrop, QtCore.QPoint(glass.S_INSET + 1,
                                               glass.S_INSET + 1))
    assert near(pixel(win, side, glass.S_INSET + 1, glass.S_INSET + 1),
                sharp.pixelColor(c), tol=12)
    # the top edge is lit: brighter than the glass just under it
    mid = side.width() // 2
    top = pixel(win, side, mid, glass.S_INSET)
    under = pixel(win, side, mid, glass.S_INSET + 6)
    assert glass.luminance(top) > glass.luminance(under) + 0.05
    # a shadow under the panel: darker than the bare backdrop there
    y = side.height() - glass.S_INSET + 4
    c = side.mapTo(win.backdrop, QtCore.QPoint(mid, y))
    assert glass.luminance(pixel(win, side, mid, y)) < \
        glass.luminance(sharp.pixelColor(c))


def test_the_top_bar_floats_with_the_backdrop_all_round(strong):
    win = strong
    QtWidgets.QApplication.processEvents()
    sharp, _ = win.backdrop.images()
    for x, y in ((2, 2), (win.bar.width() // 2, 2),
                 (win.bar.width() - 3, win.bar.height() // 2)):
        p = win.bar.mapTo(win.backdrop, QtCore.QPoint(x, y))
        assert near(pixel(win, win.bar, x, y), sharp.pixelColor(p), tol=12)


def test_the_selected_tab_glows(strong):
    win = strong
    win.show_page(2)
    QtWidgets.QApplication.processEvents()
    on, off = win.nav.button(2), win.nav.button(4)

    def green_under(b):
        c = pixel(win, b, b.width() // 2, b.height() - 5)
        return c.green() - (c.red() + c.blue()) / 2
    assert green_under(on) > green_under(off) + 8


def test_menus_and_dialogs_are_glass_in_strong(strong):
    win = strong
    menu = QtWidgets.QMenu(win)
    menu.addAction("one")
    menu.ensurePolished()
    assert menu.testAttribute(QtCore.Qt.WA_TranslucentBackground)
    from dipesh.graphical_interface.widgets import ExportDialog
    dlg = ExportDialog(win, win.s)
    m = dlg.layout().contentsMargins()
    dlg.ensurePolished()
    assert dlg.layout().contentsMargins().left() == m.left() + glass.S_INSET
    img = dlg.grab().toImage()                    # the glass card's edge
    assert glass.luminance(img.pixelColor(img.width() // 2, glass.S_INSET)) > \
        glass.luminance(img.pixelColor(img.width() // 2, glass.S_INSET + 8))
    dlg.deleteLater()
    menu.deleteLater()


# ── contrast ──────────────────────────────────────────────────────────────

ON_PANELS = [theme.TEXT, theme.PHOSPHOR, theme.AMBER, theme.RED,
             theme.ISOLATED]
IN_TABLES = ON_PANELS + theme.SERIES + list(theme.CHANNEL_COLOURS.values())


def test_subtle_text_meets_wcag_aa():
    """Every text colour reaches 4.5:1 on the lightest a panel can be, and
    on the solid colours of dialogs and pop-ups."""
    worst = glass.brightest_panel()
    for colour in ON_PANELS + [theme.MUTED]:
        assert glass.contrast(colour, worst) >= 4.5, colour
        for surface in ("#0D1C18", "#0A1617", theme._G_POP,
                        theme.PLOT["Glass"]):
            assert glass.contrast(colour, surface) >= 4.5, (colour, surface)
    field = glass.over((4, 10, 9, 150), worst)          # theme._G_FIELD
    for colour in IN_TABLES:
        assert glass.contrast(colour, field) >= 4.5, colour
    assert glass.contrast(theme.TUBE, theme.PHOSPHOR) >= 4.5
    assert glass.contrast(theme.TUBE, theme.AMBER) >= 4.5


def test_strong_text_meets_wcag_aa_on_the_lightest_glass_of_each_kind():
    """The lightest place of each Strong surface, over a whole drift cycle:
    the brightest blurred backdrop under the panel tint, fill and sheen;
    group boxes, tables, header rows, pills (and hovered pills), selections
    on top of that. Every text colour that can stand there reaches 4.5:1."""
    o = glass.over
    soft = glass.brightest_strong_backdrop()
    panel = o(glass.S_SHEEN, glass.strong_panel(soft))
    group = o((255, 255, 255, 6), panel)
    field = o((0, 0, 0, 150), group)
    header = o((255, 255, 255, 12), field)
    pill = o((255, 255, 255, 30), group)          # the top of the pill fill
    hover = o((255, 255, 255, 44), group)
    select = o((156, 255, 87, 40), field)
    menu_select = o((255, 255, 255, 30), panel)
    muted = theme.GLASS_MUTED
    checks = ([(c, s) for s in (panel, group) for c in ON_PANELS + [muted]]
              + [(c, s) for s in (field, header) for c in IN_TABLES + [muted]]
              + [(theme.TEXT, pill), (muted, pill), (theme.TEXT, hover)]
              + [(c, s) for s in (select, menu_select)
                 for c in (theme.TEXT, theme.PHOSPHOR)]
              + [(theme.TEXT, "#0E1A18"), (muted, "#0E1A18")]
              + [(c, theme.PLOT["Glass"]) for c in (theme.TEXT, theme.MUTED)]
              + [(theme.TUBE, c) for c in ("#C9FF9E", "#86E64A", "#DDFFC0",
                                           "#FFD08A", "#F0A030")])
    bad = [(c, QtGui.QColor(s).name() if not isinstance(s, str) else s,
            round(glass.contrast(c, s), 2))
           for c, s in checks if glass.contrast(c, s) < 4.5]
    assert not bad, bad


def test_muted_text_follows_the_look(window):
    assert theme.muted() == theme.MUTED
    window.s.log("a line", "info")
    look(window, "Glass", "Strong")
    assert theme.muted() == theme.GLASS_MUTED
    assert theme.GLASS_MUTED.lower() in window.console.document().toHtml().lower()
    look(window, "Glass", "Subtle")
    assert theme.muted() == theme.MUTED
    look(window, "Phosphor", "Strong")
    assert theme.muted() == theme.MUTED


# ── speed: the glass is cached, the drift is cheap and polite ─────────────

def test_strong_panels_are_cached_while_sliders_move(loaded, qtbot):
    win = loaded
    win.set_animation(False, save=False)
    look(win, "Glass", "Strong")
    win.show_page(0)
    settle(win, qtbot)
    for _ in range(3):                            # layout settled, all drawn
        QtWidgets.QApplication.processEvents()
        win.grab()
    built = win.frost.rebuilds
    frames = win.backdrop.frames
    p = win.s.params
    for t in (150, 160, 170, 140):               # drag the peak threshold
        with qtbot.waitSignal(win.s.liveChanged, timeout=30000):
            win.s.set_params(dataclasses.replace(p, abs_thresh=t))
        win.grab()
    assert win.frost.rebuilds == built            # no new glass drawn
    assert win.backdrop.frames == frames          # no new backdrop either
    win.resize(win.width() + 40, win.height())    # a resize redraws it
    QtWidgets.QApplication.processEvents()
    win.grab()
    assert win.frost.rebuilds > built
    settle(win, qtbot)


def test_the_drift_redraws_only_when_a_blob_moves_a_pixel(strong,
                                                         monkeypatch):
    win = strong
    bd = win.backdrop
    assert bd.timer.interval() == int(1000 / glass.FPS) >= 66   # <= 15 fps
    clock = [100.0]
    monkeypatch.setattr(glass.time, "monotonic", lambda: clock[0])
    bd._clock, bd.last_input = clock[0], -1e9
    bd.images()
    n = bd.frames
    clock[0] += 1 / glass.FPS                     # one tick: too little drift
    bd._tick()
    assert bd.frames == n
    clock[0] += 2.0                               # 2 s: blobs moved
    bd._tick()
    assert bd.frames == n + 1
    bd.last_input = clock[0]                      # a key was pressed just now
    clock[0] += 2.0 * glass.QUIET_S / 2.5
    bd._tick()
    assert bd.frames == n + 1
    bd.last_input = -1e9
    monkeypatch.setattr(bd, "busy", lambda: True)  # live detection at work
    clock[0] += 2.0
    bd._tick()
    assert bd.frames == n + 1
    monkeypatch.setattr(bd, "busy", lambda: False)
    t = bd.t
    monkeypatch.setattr(QtGui.QGuiApplication, "mouseButtons",
                        staticmethod(lambda: QtCore.Qt.LeftButton))
    clock[0] += 2.0                               # a slider is held
    bd._tick()
    assert bd.frames == n + 1 and bd.t > t        # time runs, no redraw
    # a full cycle is CYCLE seconds
    a = glass.blob_centres(1000, 800, 3.0)
    b = glass.blob_centres(1000, 800, 3.0 + glass.CYCLE)
    assert all(abs(p - q) < 1e-6 for u, v in zip(a, b) for p, q in zip(u, v))


def test_the_drift_follows_the_toggle_and_reduced_motion(strong,
                                                        monkeypatch):
    win = strong
    from dipesh.graphical_interface import main_window
    monkeypatch.setattr(main_window, "reduced_motion", lambda: False)
    win.set_animation(True, save=False)
    assert win.backdrop.timer.isActive()
    win.set_animation(False, save=False)
    assert not win.backdrop.timer.isActive()
    monkeypatch.setattr(main_window, "reduced_motion", lambda: True)
    win.set_animation(True, save=False)
    assert not win.backdrop.timer.isActive()      # the system asked for less
    monkeypatch.setattr(main_window, "reduced_motion", lambda: False)
    win.set_animation(True, save=False)
    look(win, "Glass", "Subtle")                  # only Strong drifts
    assert not win.backdrop.timer.isActive()
    look(win, "Phosphor", "Strong")
    assert not win.backdrop.timer.isActive()


def test_reduced_motion_can_be_asked_without_failing():
    assert glass.reduced_motion() in (True, False)


# ── the Windows 11 frame ──────────────────────────────────────────────────

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


@pytest.mark.parametrize("look, level", LOOKS)
def test_number_boxes_show_their_text(window, look, level):
    """Qt 6.12 leaves the text of a box without arrows 1 px wide unless the
    style sheet says where its (missing) arrows sit."""
    window.set_glass_intensity(level, save=False)
    window.set_theme(look, save=False)
    window.show_page(0)
    QtWidgets.QApplication.processEvents()
    boxes = [b for b in window.findChildren(QtWidgets.QAbstractSpinBox)
             if b.isVisible()]
    assert boxes
    for b in boxes:
        assert b.lineEdit().width() >= b.width() // 2, b.text()
    window.set_theme("Phosphor", save=False)
