"""
The image lesson: what the detection and the spot measurement compute,
shown on the frame you are looking at.

    left    two zoomed windows of the frame: "event", centred on one detected
            spot, and "background", on a patch with no spot
    middle  the event's measurements, and a text that follows the mouse
    right   learn's own copy of the detection panel (settings.py, placed by
            the learn page): resting the mouse on any of its numbers or
            settings draws what it does in the windows and explains it in
            the text. Its settings reach the analysis only with Apply.
"""

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from ..pages.base import empty_overlay, qcolor
from ..pages.image import phosphor_map
from ..theme import (AMBER, ISOLATED, PANEL, PHOSPHOR,
                                         RED, TEXT, plot_background)
from ...single_image_analysis import load_item
from .crops import aperture, event_order, quiet_window, stages, window_at
from .textfile import LessonText

# which image each topic is drawn on
SHOWN = {
    "sigma": "residual",
    "thresh": "diff", "abs_thresh": "diff", "n_sigma": "diff",
    "adaptive": "diff", "lum": "diff", "sum_thresh": "diff",
    "spread_min": "diff", "min_dist": "diff", "spot_max_radius": "diff",
    "bg_blur_size": "background",
}

# the rows of the event table each topic is about
ROWS = {
    "thresh": ["peak"], "abs_thresh": ["peak"], "n_sigma": ["peak"],
    "adaptive": ["peak"], "sum_thresh": ["5x5 sum"],
    "spread_min": ["peak", "5x5 sum", "spread"],
    "spot_max_radius": ["luminosity", "aperture radius", "area"],
    "iso": ["nearest neighbour", "isolated"],
    "isolation_factor": ["nearest neighbour", "isolated"],
    "lum": ["luminosity"],
}

TABLE = ["position", "peak", "5x5 sum", "spread", "luminosity",
         "aperture radius", "area", "radial σ", "concentration",
         "eccentricity", "profile slope", "nearest neighbour", "isolated"]


def _g(v, digits=4):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    return f"{v:.{digits}g}"


class CropView(QtWidgets.QWidget):
    """One zoomed window of the frame, drawn in frame pixel coordinates,
    with room for the marks a topic adds on top."""

    def __init__(self, name):
        super().__init__()
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        head = QtWidgets.QHBoxLayout()
        self.name = QtWidgets.QLabel(name)
        self.name.setObjectName("heading")
        head.addWidget(self.name)
        head.addStretch(1)
        self.where = QtWidgets.QLabel("")
        self.where.setObjectName("muted")
        head.addWidget(self.where)
        lay.addLayout(head)
        self.head = head

        self.gw = pg.GraphicsLayoutWidget()
        self.gw.setBackground(plot_background())
        self.vb = self.gw.addViewBox()
        self.vb.invertY(True)
        self.vb.setAspectLocked(True)
        self.vb.setMouseEnabled(False, False)
        self.vb.setMenuEnabled(False)
        self.img = pg.ImageItem()
        self.img.setColorMap(phosphor_map())
        self.vb.addItem(self.img)
        self.over = pg.ImageItem()                 # coloured pixel marks
        self.over.setZValue(5)
        self.vb.addItem(self.over)
        lay.addWidget(self.gw, 1)
        self.marks = []
        self.win = None

    def show_image(self, full, win, levels):
        self.win = win
        self.img.setImage(win.cut(full), levels=levels)
        self.img.setRect(self._rect())
        self.over.clear()
        self.vb.setRange(xRange=(win.x0, win.x1), yRange=(win.y0, win.y1),
                         padding=0)
        self.where.setText(f"x {win.x0}–{win.x1 - 1}   y {win.y0}–{win.y1 - 1}")

    def _rect(self):
        w = self.win
        return QtCore.QRectF(w.x0, w.y0, w.x1 - w.x0, w.y1 - w.y0)

    def clear_image(self):
        self.win = None
        self.img.clear()
        self.over.clear()
        self.where.setText("")
        self.clear_marks()

    def clear_marks(self):
        for m in self.marks:
            self.vb.removeItem(m)
        self.marks = []

    def _add(self, item, z=10):
        item.setZValue(z)
        self.vb.addItem(item)
        self.marks.append(item)
        return item

    def pixels(self, mask_full, colour, alpha=190):
        """Fill the window's pixels where mask_full is true."""
        if self.win is None:
            return 0
        m = self.win.cut(mask_full)
        rgba = np.zeros(m.shape + (4,), np.ubyte)
        c = QtGui.QColor(colour)
        rgba[m] = (c.red(), c.green(), c.blue(), alpha)
        self.over.setImage(rgba, levels=(0, 255))
        self.over.setRect(self._rect())
        return int(m.sum())

    def boxes(self, mask_full, colour):
        """Outline each pixel of the window where mask_full is true."""
        if self.win is None:
            return 0
        ys, xs = np.nonzero(self.win.cut(mask_full))
        for y, x in zip(ys, xs):
            self.box(self.win.x0 + x, self.win.y0 + y, 1, 1, colour, 1.6)
        return len(xs)

    def circle(self, x, y, r, colour, width=1.6, dashed=False):
        """A circle of radius r around the centre of pixel (x, y)."""
        e = QtWidgets.QGraphicsEllipseItem(x + 0.5 - r, y + 0.5 - r, 2 * r, 2 * r)
        pen = QtGui.QPen(QtGui.QColor(colour), width,
                         QtCore.Qt.DashLine if dashed else QtCore.Qt.SolidLine)
        pen.setCosmetic(True)
        e.setPen(pen)
        return self._add(e)

    def box(self, x0, y0, w, h, colour, width=1.6, dashed=False):
        r = QtWidgets.QGraphicsRectItem(x0, y0, w, h)
        pen = QtGui.QPen(QtGui.QColor(colour), width,
                         QtCore.Qt.DashLine if dashed else QtCore.Qt.SolidLine)
        pen.setCosmetic(True)
        r.setPen(pen)
        return self._add(r)

    def line(self, x0, y0, x1, y1, colour, width=1.2):
        ln = QtWidgets.QGraphicsLineItem(x0 + 0.5, y0 + 0.5, x1 + 0.5, y1 + 0.5)
        pen = QtGui.QPen(QtGui.QColor(colour), width, QtCore.Qt.DotLine)
        pen.setCosmetic(True)
        ln.setPen(pen)
        return self._add(ln)

    def points(self, xs, ys, colour, symbol="x", size=11):
        s = pg.ScatterPlotItem(x=np.asarray(xs) + 0.5, y=np.asarray(ys) + 0.5,
                               symbol=symbol, size=size, brush=None,
                               pen=pg.mkPen(colour, width=1.6))
        return self._add(s, 11)

    def label(self, x, y, text, colour):
        t = pg.TextItem(text, color=colour, anchor=(0, 1))
        t.setPos(x, y)
        return self._add(t, 12)


COLOURS = {"amber": AMBER, "white": ISOLATED, "red": RED, "green": PHOSPHOR}
SHAPES = ["dashed circle", "dashed box", "dashed line", "circle", "box",
          "fill", "x", "ring", "line", "dot", "plus"]


def mark_icon(mark, w=26, h=18):
    """The icon of one legend mark, e.g. "amber fill" or "white dashed
    circle", drawn the way the windows draw it. None if it is not one."""
    words = mark.split()
    if not words or words[0] not in COLOURS:
        return None
    shape = " ".join(words[1:])
    if shape not in SHAPES:
        return None
    c = QtGui.QColor(COLOURS[words[0]])
    pm = QtGui.QPixmap(w, h)
    pm.fill(QtGui.QColor(PANEL))
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    dashed = shape.startswith("dashed")
    pen = QtGui.QPen(c, 1.6, QtCore.Qt.DashLine if dashed else
                     QtCore.Qt.SolidLine)
    p.setPen(pen)
    p.setBrush(QtCore.Qt.NoBrush)
    m = QtCore.QRectF(w / 2 - 7, h / 2 - 7, 14, 14)
    if shape.endswith("circle"):
        p.drawEllipse(m)
    elif shape.endswith("box"):
        p.drawRect(m.adjusted(2, 2, -2, -2))
    elif shape == "fill":
        f = QtGui.QColor(c)
        f.setAlpha(190)
        p.fillRect(m.adjusted(1, 1, -1, -1), f)
    elif shape == "x":
        p.drawLine(m.topLeft() + QtCore.QPointF(2, 2),
                   m.bottomRight() - QtCore.QPointF(2, 2))
        p.drawLine(m.topRight() + QtCore.QPointF(-2, 2),
                   m.bottomLeft() + QtCore.QPointF(2, -2))
    elif shape == "ring":
        p.drawEllipse(m.adjusted(2, 2, -2, -2))
    elif shape == "line":
        p.setPen(QtGui.QPen(c, 1.8))
        p.drawLine(QtCore.QPointF(2, h / 2), QtCore.QPointF(w - 2, h / 2))
    elif shape == "dashed line":
        p.setPen(QtGui.QPen(c, 1.6, QtCore.Qt.DashLine))
        p.drawLine(QtCore.QPointF(2, h / 2), QtCore.QPointF(w - 2, h / 2))
    elif shape == "dot":
        p.setBrush(c)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(QtCore.QPointF(w / 2, h / 2), 3, 3)
    elif shape == "plus":
        p.setPen(QtGui.QPen(c, 1.8))
        p.drawLine(QtCore.QPointF(w / 2 - 6, h / 2), QtCore.QPointF(w / 2 + 6, h / 2))
        p.drawLine(QtCore.QPointF(w / 2, h / 2 - 6), QtCore.QPointF(w / 2, h / 2 + 6))
    p.end()
    return pm


def scale_icon(w=60, h=12):
    """The colour scale of the windows, dark to bright."""
    cmap = phosphor_map()
    pm = QtGui.QPixmap(w, h)
    p = QtGui.QPainter(pm)
    for x in range(w):
        p.setPen(cmap.map(x / (w - 1), mode="qcolor"))
        p.drawLine(x, 0, x, h)
    p.end()
    return pm


class Legend(QtWidgets.QWidget):
    """What the marks in the two windows mean, for the topic on show."""

    def __init__(self):
        super().__init__()
        self.grid = QtWidgets.QGridLayout(self)
        self.grid.setContentsMargins(0, 2, 0, 0)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(3)
        self.grid.setColumnStretch(1, 1)
        self.scale = scale_icon()

    def show_items(self, shown, levels, items):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w is not None:
                w.hide()                 # gone now, not at the next event loop
                w.deleteLater()
        rows = []
        if shown:
            lo, hi = levels if levels else ("", "")
            rng = f"  ({lo:.0f} → {hi:.0f})" if levels else ""
            rows.append((self.scale, f"image: {shown}{rng}"))
        for mark, meaning in items:
            icon = mark_icon(mark)
            rows.append((icon, meaning if icon is not None or not mark
                         else f"{mark} = {meaning}"))
        for r, (icon, text) in enumerate(rows):
            if icon is not None:
                a = QtWidgets.QLabel()
                a.setPixmap(icon)
                a.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
                self.grid.addWidget(a, r, 0)
            b = QtWidgets.QLabel(text)
            b.setObjectName("muted")
            b.setWordWrap(True)
            self.grid.addWidget(b, r, 1)


class ImageLesson(QtWidgets.QWidget):
    title = "image"
    uses_detection = True            # learn's detection panel on the right

    def __init__(self, session):
        """session: learn's own (LearnSettings.s)."""
        super().__init__()
        self.s = session
        self.topic = None
        self.st = None                       # Stages of the current frame
        self.spots = []
        self.order = []
        self.k = 0                           # position in self.order
        self.ap = None                       # the event's Aperture
        self.ev_win = self.bg_win = None
        self._img = self._img_path = None
        self._params = None                  # the params self.st was made with
        self._dirty = True
        self.watch = None

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        # column 1: the two windows
        left = QtWidgets.QWidget()
        lv = QtWidgets.QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(8)
        self.event = CropView("event")
        self.prev = self._step_button("◀", "Previous spot", -1)
        self.next = self._step_button("▶", "Next spot", 1)
        self.which = QtWidgets.QLabel("")
        self.which.setObjectName("muted")
        self.event.head.insertWidget(1, self.prev)
        self.event.head.insertWidget(2, self.which)
        self.event.head.insertWidget(3, self.next)
        self.background = CropView("background")
        lv.addWidget(self.event, 1)
        lv.addWidget(self.background, 1)
        self.legend = Legend()
        lv.addWidget(self.legend)
        self.levels = None
        row.addWidget(left, 1)

        # column 2: the event's numbers and the text
        mid = QtWidgets.QWidget()
        mv = QtWidgets.QVBoxLayout(mid)
        mv.setContentsMargins(0, 0, 0, 0)
        mv.setSpacing(6)
        lab = QtWidgets.QLabel("the event")
        lab.setObjectName("heading")
        mv.addWidget(lab)
        self.table = QtWidgets.QTableWidget(len(TABLE), 3)
        self.table.setHorizontalHeaderLabels(["feature", "value", "cut"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(QtCore.Qt.NoFocus)
        self.table.setAlternatingRowColors(True)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        for i, name in enumerate(TABLE):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(name))
            for j in (1, 2):
                it = QtWidgets.QTableWidgetItem("–")
                it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(i, j, it)
        self.table.resizeRowsToContents()
        h = (self.table.horizontalHeader().sizeHint().height() +
             sum(self.table.rowHeight(i) for i in range(len(TABLE))) + 4)
        self.table.setFixedHeight(h)
        mv.addWidget(self.table)
        self.heading = QtWidgets.QLabel("")
        self.heading.setObjectName("heading")
        self.heading.setWordWrap(True)
        mv.addWidget(self.heading)
        self.text = QtWidgets.QTextBrowser()
        self.text.setOpenLinks(False)
        mv.addWidget(self.text, 1)
        # the words come from a Markdown file, read again whenever it is saved
        self.words = LessonText("image.md")
        self.words.changed.connect(self._show_text)
        src = QtWidgets.QLabel(f"text from learn/texts/image.md — save it and "
                               f"the change shows here")
        src.setObjectName("muted")
        src.setToolTip(self.words.path)
        src.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        mv.addWidget(src)
        row.addWidget(mid, 1)

        self.empty = empty_overlay(self, "Select a run in the list on the "
                                   "left to see the lesson on its image.\n"
                                   "Ctrl+O adds a folder of runs.")

        # back to the introduction shortly after the mouse leaves the panel,
        # unless it lands on another topic first
        self.idle = QtCore.QTimer(self)
        self.idle.setSingleShot(True)
        self.idle.setInterval(250)
        self.idle.timeout.connect(lambda: self.set_topic(None))

        session.currentChanged.connect(self._mark)
        session.liveChanged.connect(self._mark)
        self._show_text()

    def _step_button(self, text, tip, step):
        b = QtWidgets.QToolButton()
        b.setText(text)
        b.setToolTip(tip)
        b.setAutoRaise(True)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.clicked.connect(lambda: self.step(step))
        return b

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty.setGeometry(self.rect())

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh()

    # data
    def _mark(self, *_):
        self._dirty = True
        if self.isVisible():
            self.refresh()

    def refresh(self):
        if not self._dirty:
            return
        self._dirty = False
        cur, r = self.s.current, self.s.live
        ready = (cur is not None and r is not None and r.ok
                 and r.item is cur[1])
        self.empty.setVisible(cur is None)
        self.empty.raise_()
        if not ready:
            if cur is None:
                self.st = None
                self.event.clear_image()
                self.background.clear_image()
                self._fill_table()
                self._show_text()
            return
        item = cur[1]
        if item.key != self._img_path:
            self._img, self._img_path = load_item(item), item.key
            self.st = None
        if self._img is None:
            return
        # the event stays the same spot while settings move, if it survives
        old = (self.spots[self.order[self.k]] if self.order else None)
        self.st = stages(self._img, self.s.params)
        self.spots = r.spots
        self.info = r.info
        self.order = event_order(self.spots)
        self.k = 0
        if old is not None and self.order:
            d = [abs(self.spots[i].x - old.x) + abs(self.spots[i].y - old.y)
                 for i in self.order]
            if min(d) <= 3:
                self.k = int(np.argmin(d))
        self._place()

    def step(self, d):
        if self.order:
            self.k = (self.k + d) % len(self.order)
            self._place()

    def _half(self):
        """Half the window side: room for the spot's largest aperture, and
        for whatever the current topic draws around it."""
        p, ev = self.s.params, self.event_spot()
        half = max(24, p.spot_max_radius + 8)
        if self.topic == "bg_blur_size":
            half = max(half, p.bg_blur_size // 2 + 4)
        elif self.topic in ("iso", "isolation_factor") and ev is not None:
            half = max(half, int(np.ceil(p.isolation_factor *
                                         ev.radius_used)) + 4)
        elif self.topic == "min_dist":
            half = max(half, p.min_dist + 6)
        return int(half)

    def _windows(self):
        st, p, ev = self.st, self.s.params, self.event_spot()
        half, shape = self._half(), st.diff.shape
        self.ev_win = (window_at(ev.x, ev.y, half, shape) if ev is not None
                       else None)
        self.bg_win = quiet_window(self.spots, half, shape, p.mcp_region)

    def _place(self):
        """Measure the event and redraw everything."""
        st, p = self.st, self.s.params
        if st is None:
            return
        if self.order:
            ev = self.spots[self.order[self.k]]
            self.ap = aperture(st, ev, self.info.bg_residual, p)
            self.which.setText(f"{self.k + 1} / {len(self.order)}")
        else:
            self.ap = None
            self.which.setText("no spot")
        self.prev.setEnabled(len(self.order) > 1)
        self.next.setEnabled(len(self.order) > 1)
        self._fill_table()
        self._draw()

    def event_spot(self):
        return self.spots[self.order[self.k]] if self.order else None

    # the event table
    def _fill_table(self):
        s, p = self.event_spot(), self.s.params
        thresh = self.st.thresh if self.st else None
        if s is None:
            vals = {n: ("–", "") for n in TABLE}
        else:
            spread = s.sum5x5 / s.peak if s.peak > 0 else float("nan")
            ok = lambda b: "✓" if b else "✗"         # noqa: E731
            vals = {
                "position": (f"{s.x}, {s.y}", ""),
                "peak": (_g(s.peak), f"> {thresh:.0f} {ok(s.peak > thresh)}"),
                "5x5 sum": (_g(s.sum5x5),
                            f"> {p.sum_thresh:g} {ok(s.sum5x5 > p.sum_thresh)}"),
                "spread": (_g(spread),
                           f"> {p.spread_min:g} {ok(spread > p.spread_min)}"),
                "luminosity": (_g(s.luminosity), ""),
                "aperture radius": (f"{s.radius_used} px",
                                    f"≤ {p.spot_max_radius} px"),
                "area": (f"{s.area} px", ""),
                "radial σ": (_g(s.radial_sigma) + " px", ""),
                "concentration": (_g(s.concentration), ""),
                "eccentricity": (_g(s.eccentricity), ""),
                "profile slope": (_g(s.profile_slope), ""),
                "nearest neighbour": ((_g(s.nn_dist) + " px")
                                      if np.isfinite(s.nn_dist) else "∞", ""),
                "isolated": ("yes" if s.is_isolated else "no",
                             f"> {p.isolation_factor * s.radius_used:.3g} px"),
            }
        rows = set(ROWS.get(self.topic, []))
        for i, name in enumerate(TABLE):
            v, c = vals[name]
            self.table.item(i, 1).setText(v)
            self.table.item(i, 2).setText(c)
            hot = name in rows
            for j in range(3):
                it = self.table.item(i, j)
                it.setBackground(qcolor(PHOSPHOR, 45) if hot
                                 else QtGui.QBrush())
                it.setForeground(QtGui.QColor(
                    RED if c.endswith("✗") and j == 2 else
                    PHOSPHOR if hot else TEXT))

    # hover
    def set_topic(self, key):
        """Show one topic, or the introduction for None."""
        if key is None and self.topic is None:
            return
        if key is not None:
            self.idle.stop()
        if key == self.topic:
            return
        self.topic = key
        self._fill_table()
        self._draw()

    def hovered(self, key):
        """From the panel watcher: the mouse rests on key, or on nothing."""
        if not self.isVisible():
            return
        if key:
            self.set_topic(key)
        else:
            self.idle.start()

    # drawing
    def _levels(self, mode):
        st = self.st
        ev, bg = self.ev_win, self.bg_win
        wins = [w for w in (ev, bg) if w is not None]
        if mode in ("diff",):
            top = max([float(w.cut(st.diff).max()) for w in wins] + [1.0])
            return (0.0, max(top, 1.0))
        if mode == "residual":
            a = np.concatenate([w.cut(st.cleaned - st.first_pass).ravel()
                                for w in wins])
            lo, hi = float(np.percentile(a, 1)), float(a.max())
            return (lo, hi if hi > lo else lo + 1)
        # camera, cleaned and background share the camera's levels, so the
        # background estimate reads on the same scale as the image
        a = np.concatenate([w.cut(st.camera).ravel() for w in wins])
        lo, hi = float(np.percentile(a, 1)), float(np.percentile(a, 99.9))
        return (lo, hi if hi > lo else lo + 1)

    def _frame(self, mode):
        st = self.st
        return {"camera": st.camera, "diff": st.diff,
                "background": st.background,
                "residual": st.cleaned - st.first_pass}[mode]

    def _draw(self):
        for v in (self.event, self.background):
            v.clear_marks()
        st = self.st
        if st is None:
            self.levels = None
            self._show_text()
            return
        self._windows()
        mode = SHOWN.get(self.topic, "camera")
        full, levels = self._frame(mode), self._levels(mode)
        self.levels = levels
        self._show_text()
        if self.ev_win is not None:
            self.event.show_image(full, self.ev_win, levels)
        else:
            self.event.clear_image()
        self.background.show_image(full, self.bg_win, levels)
        self._marks()

    def _marks(self):
        """What the current topic draws on top of the two windows."""
        st, p, key = self.st, self.s.params, self.topic
        ev, ap = self.event_spot(), self.ap
        views = [v for v in (self.event, self.background) if v.win is not None]
        others = [s for s in self.spots if s is not ev]

        def spots_in(v, spots):
            w = v.win
            return [s for s in spots if w.x0 - 30 <= s.x < w.x1 + 30
                    and w.y0 - 30 <= s.y < w.y1 + 30]

        if key in (None, "count", "detection", "measurement"):
            for v in views:
                for s in spots_in(v, self.spots):
                    v.circle(s.x, s.y, s.radius_used + 0.5,
                             ISOLATED if s.is_isolated else AMBER)
            if key == "count":
                self._suppressed(views)
            return
        if key == "sigma":
            for v in views:
                v.pixels(st.masked, AMBER)
            return
        if key in ("thresh", "adaptive", "abs_thresh", "n_sigma"):
            level = {"abs_thresh": p.abs_thresh,
                     "n_sigma": p.n_sigma * st.sigma}.get(key, st.thresh)
            for v in views:
                v.pixels(st.diff > level, AMBER)
            if ev is not None:
                self.event.box(ev.x, ev.y, 1, 1, ISOLATED, 2)
            return
        if key in ("hot", "hotpix_delta"):
            for v in views:
                v.boxes(st.hot, RED)
            return
        if key == "lum":
            if ev is not None:
                self.event.circle(ev.x, ev.y, p.aperture_radius + 0.5, ISOLATED)
            return
        if key in ("sum_thresh", "spread_min"):
            if ev is not None:
                self.event.box(ev.x - 2, ev.y - 2, 5, 5, AMBER)
                self.event.box(ev.x, ev.y, 1, 1, ISOLATED, 2)
            return
        if key == "min_dist":
            if ev is not None:
                self.event.circle(ev.x, ev.y, p.min_dist, AMBER)
            self._suppressed(views)
            for v in views:
                for s in spots_in(v, others):
                    v.circle(s.x, s.y, p.min_dist, AMBER, 1.0, dashed=True)
            return
        if key == "bg_blur_size":
            k = p.bg_blur_size if p.bg_blur_size % 2 else p.bg_blur_size + 1
            for v in views:
                cx, cy = v.win.centre
                v.box(cx - k / 2, cy - k / 2, k, k, AMBER, dashed=True)
            return
        if key == "spot_max_radius":
            if ev is not None:
                self.event.circle(ev.x, ev.y, p.spot_max_radius + 0.5, AMBER,
                                  1.2, dashed=True)
                self.event.circle(ev.x, ev.y, ev.radius_used + 0.5, ISOLATED)
            return
        if key in ("iso", "isolation_factor"):
            if ev is None:
                return
            v = self.event
            v.circle(ev.x, ev.y, ev.radius_used + 0.5, ISOLATED)
            v.circle(ev.x, ev.y, p.isolation_factor * ev.radius_used,
                     ISOLATED if ev.is_isolated else AMBER, 1.2, dashed=True)
            near = spots_in(v, others)
            if near:
                v.points([s.x for s in near], [s.y for s in near], RED, "o", 12)
            if others and np.isfinite(ev.nn_dist):
                nn = min(others, key=lambda s: (s.x - ev.x) ** 2 + (s.y - ev.y) ** 2)
                v.line(ev.x, ev.y, nn.x, nn.y, RED)

    def _suppressed(self, views):
        """Mark the candidate pixels that passed every cut but were dropped
        for being too close to a brighter spot."""
        kept = np.zeros(self.st.candidates.shape, bool)
        for s in self.spots:
            kept[s.y, s.x] = True
        drop = self.st.candidates & ~kept
        for v in views:
            ys, xs = np.nonzero(v.win.cut(drop))
            if len(xs):
                v.points(xs + v.win.x0, ys + v.win.y0, RED, "x", 10)

    # text
    def _fields(self):
        st, p, ev, ap = self.st, self.s.params, self.event_spot(), self.ap
        f = {
            "abs_thresh": f"{p.abs_thresh:g}", "n_sigma": f"{p.n_sigma:g}",
            "sum_thresh": f"{p.sum_thresh:g}", "spread_min": f"{p.spread_min:g}",
            "min_dist": f"{p.min_dist}", "hotpix_delta": f"{p.hotpix_delta:g}",
            "kernel": f"{p.bg_blur_size if p.bg_blur_size % 2 else p.bg_blur_size + 1}",
            "adaptive": "on" if p.adaptive else "off",
            "spot_max_radius": f"{p.spot_max_radius}",
            "isolation_factor": f"{p.isolation_factor:g}",
            "aperture_radius": f"{p.aperture_radius}",
            "mask_nsigma": f"{p.mask_nsigma:g}",
            "plateau_pct": f"{100 * p.plateau_frac:g}",
            "nms": f"{p.nms_size if p.nms_size % 2 else p.nms_size + 1}",
        }
        if st is None:
            return f
        nsig = p.n_sigma * st.sigma
        f.update({
            "n": str(len(self.spots)),
            "sigma": f"{st.sigma:.2f}", "thresh": f"{st.thresh:.0f}",
            "nsig": f"{nsig:.1f}",
            "mask_level": f"{p.mask_nsigma * st.sigma:.1f}",
            "n_hot": str(int(st.hot.sum())),
            "n_iso": str(sum(s.is_isolated for s in self.spots)),
            "lum_count": f"{self.info.pbar_count_lum:.1f}",
            "bg_res": f"{self.info.bg_residual:.2f}",
        })
        if p.adaptive and nsig > p.abs_thresh:
            f["thresh_rule"] = (
                f"Adaptive thresholding is now **on**. On this frame noise "
                f"multiple × σ = {p.n_sigma:g} × {st.sigma:.2f} = {nsig:.1f} "
                f"is higher than the peak threshold ({p.abs_thresh:g}), so the "
                f"threshold used is noise multiple × σ: **{st.thresh:.0f}**.")
        elif p.adaptive:
            f["thresh_rule"] = (
                f"Adaptive thresholding is now **on**. On this frame noise "
                f"multiple × σ = {p.n_sigma:g} × {st.sigma:.2f} = {nsig:.1f} "
                f"is lower than the peak threshold ({p.abs_thresh:g}), so the "
                f"threshold used is the peak threshold: **{st.thresh:.0f}**.")
        else:
            f["thresh_rule"] = (
                f"Adaptive thresholding is now **off**, so the threshold used "
                f"is the peak threshold: **{st.thresh:.0f}**.")
        f["abs_note"] = (
            f"On this frame adaptive thresholding is on and noise multiple × "
            f"σ = {nsig:.1f} is higher than the peak threshold, so the "
            f"threshold used is {st.thresh:.0f}, not the peak threshold. "
            f"Moving the peak threshold changes nothing until the peak "
            f"threshold is above {nsig:.1f}."
            if p.adaptive and nsig > p.abs_thresh else "")
        kept = np.zeros(st.candidates.shape, bool)
        for s in self.spots:
            kept[s.y, s.x] = True
        f["n_suppressed"] = str(int((st.candidates & ~kept).sum()))
        for name, win in (("ev", self.ev_win), ("bg", self.bg_win)):
            if win is None:
                continue
            f[f"hot_{name}"] = str(int(win.cut(st.hot).sum()))
            f[f"masked_{name}"] = str(int(win.cut(st.masked).sum()))
            f[f"bg_{name}"] = (f"{float(win.cut(st.background).mean()):.1f} "
                               f"on average")
        if self.bg_win is not None:
            n_above = int((self.bg_win.cut(st.diff) > st.thresh).sum())
            f["above_bg"] = ("none" if n_above == 0 else
                             f"{n_above} pixel{'s' if n_above > 1 else ''}")
        if ev is not None:
            spread = ev.sum5x5 / ev.peak if ev.peak > 0 else float("nan")
            # a verb: the texts say "the peak {pass_peak} the cut"
            passes = lambda b: ("**passes**" if b else    # noqa: E731
                                f"<span style='color:{RED}'>**fails**</span>")
            f.update({
                "ev_peak": f"{ev.peak:.1f}", "ev_sum5": f"{ev.sum5x5:.0f}",
                "ev_spread": f"{spread:.1f}",
                "ev_lum": f"{ev.luminosity:.0f}",
                "ev_r": str(ev.radius_used), "ev_area": str(ev.area),
                # a lone spot has no neighbour: its distance is infinite
                "ev_nn": (_g(ev.nn_dist) + " px" if np.isfinite(ev.nn_dist)
                          else "∞ (no other spot in this image)"),
                "ev_iso": "isolated" if ev.is_isolated else "crowded",
                "iso_r": f"{p.isolation_factor * ev.radius_used:.3g}",
                "pass_peak": passes(ev.peak > st.thresh),
                "pass_abs": passes(ev.peak > p.abs_thresh),
                "pass_sum": passes(ev.sum5x5 > p.sum_thresh),
                "pass_spread": passes(spread > p.spread_min),
                "stop_reason": self._stop_reason(ev),
            })
        return f

    def _stop_reason(self, ev):
        p = self.s.params
        if ev.radius_used < p.spot_max_radius or self.ap is None:
            return "its light stopped growing"
        # at the max radius: did the last ring still add light?
        ap, R = self.ap, p.spot_max_radius
        inner = ap.r2 <= (R - 1) ** 2
        outer = ap.r2 <= R * R
        lum = lambda m: float(ap.sub[m].sum() - ap.bg_res * m.sum())  # noqa: E731
        a, b = lum(inner), lum(outer)
        if a > 0 and (b - a) < p.plateau_frac * a:
            return "its light stopped growing just at the max aperture"
        return "it reached the max aperture with its light still growing"

    def _show_text(self):
        title, shown, legend, body = self.words.render(self.topic or "intro",
                                                       self._fields())
        self.heading.setText(title)
        self.legend.show_items(shown, self.levels, legend)
        self.text.setMarkdown(body)
