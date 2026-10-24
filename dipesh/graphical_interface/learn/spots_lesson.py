"""
The spots lesson: what each column of the spot table measures, drawn on
the spot it was measured on.

    top     the spots page itself: its controls and its table, as on the
            spots page, filled with learn's live detection
    bottom  the spot of the row the mouse is on (or the row clicked), zoomed,
            with what the column under the mouse measures drawn on it; its
            radial profile; a legend; and the description
    right   learn's detection panel, as on the spots page (placed by the page)

Resting on a column header explains that feature on the selected spot;
resting on a cell explains it on that row's spot.
"""

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from ..pages.base import empty_overlay
from ..pages.spots import SPOT_COLS, SpotsPage
from ..theme import (AMBER, ISOLATED, PHOSPHOR, RED,
                                         scope_plot)
from ...features import profile_fit, second_moments
from ...single_image_analysis import load_item
from .crops import aperture, stages, window_at
from .description import Description
from .hover import HoverWatch, map_control
from .image_lesson import CropView, Legend

COLUMN = {i: (attr or "spot") for i, (_, attr) in enumerate(SPOT_COLS)}
FEATURES = {"luminosity", "radius_used", "area", "peak", "sum5x5",
            "radial_sigma", "concentration", "eccentricity", "profile_slope",
            "nn_dist", "is_isolated"}


class _Spots(SpotsPage):
    """The spots page, unchanged; a double-click selects the spot here
    instead of jumping to the image page."""

    def __init__(self, session, on_pick):
        super().__init__(session)
        self.on_pick = on_pick

    def _goto(self, row, _col):
        data = self.table.item(row, 0).data(QtCore.Qt.UserRole)
        if data:
            self.on_pick(*data)


class SpotsLesson(QtWidgets.QWidget):
    title = "spots"
    uses_detection = True

    def __init__(self, session, main):
        """session: learn's own (live spots with learn's settings);
        main: the program's (the dataset results of the last Run all)."""
        super().__init__()
        self.s, self.main = session, main
        self.topic = None
        self.picked = None                  # (RunResult, Spot) clicked
        self.hover_spot = None              # (RunResult, Spot) under the mouse
        self._cache = {}

        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(8)
        self.page = _Spots(session, self.pick)
        self.page.layout().setContentsMargins(0, 0, 0, 0)
        col.addWidget(self.page, 3)

        low = QtWidgets.QHBoxLayout()
        low.setSpacing(10)
        fig = QtWidgets.QVBoxLayout()
        fig.setSpacing(4)
        figs = QtWidgets.QHBoxLayout()
        self.view = CropView("the spot")
        figs.addWidget(self.view, 1)
        pbox = QtWidgets.QWidget()
        pl = QtWidgets.QVBoxLayout(pbox)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(2)
        lab = QtWidgets.QLabel("radial profile")
        lab.setObjectName("heading")
        pl.addWidget(lab)
        self.profile = scope_plot("distance from the centroid (px)",
                                  "log light per pixel")
        pl.addWidget(self.profile, 1)
        figs.addWidget(pbox, 1)
        fig.addLayout(figs, 1)
        self.legend = Legend()
        fig.addWidget(self.legend)
        low.addLayout(fig, 3)
        self.empty = empty_overlay(self.view, "Select a run in the list on "
                                   "the left:\nits spots fill the table.")
        self.desc = Description("spots.md")
        self.desc.connect_changed(self._draw)
        low.addWidget(self.desc, 2)
        col.addLayout(low, 4)

        t = self.page.table
        self.watch = HoverWatch([self.page], self.hovered, resolvers={
            t.viewport(): self._cell, t.horizontalHeader(): self._header})
        map_control(self.watch, self.page.scope, "scope")
        self.watch.add(self.page.iso_only, "iso_only")
        self.watch.add(self.page.info, "info")
        for b in self.page.findChildren(QtWidgets.QPushButton):
            self.watch.add(b, "save")

        self.idle = QtCore.QTimer(self)
        self.idle.setSingleShot(True)
        self.idle.setInterval(250)
        self.idle.timeout.connect(self._to_intro)

        t.currentCellChanged.connect(self._clicked)
        session.liveChanged.connect(self._later)
        session.currentChanged.connect(self._later)
        main.resultsChanged.connect(self._later)
        self.page.scope.currentIndexChanged.connect(self._later)
        self.page.iso_only.toggled.connect(self._later)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty.setGeometry(self.view.rect())

    # hover
    def _cell(self, viewport, pos):
        idx = self.page.table.indexAt(pos)
        if not idx.isValid():
            return None
        return (COLUMN[idx.column()], idx.row())

    def _header(self, header, pos):
        c = header.logicalIndexAt(pos)
        return (COLUMN[c], None) if c >= 0 else None

    def hovered(self, key):
        if not self.isVisible():
            return
        if key is None:
            self.idle.start()
            return
        self.idle.stop()
        if isinstance(key, tuple):
            topic, row = key
            self.hover_spot = self._row_spot(row) if row is not None else None
        else:
            topic, self.hover_spot = key, None
        self.topic = topic
        self._draw()

    def panel_hovered(self, key):
        """The mouse on the detection panel: one topic for all of it."""
        self.hovered("panel" if key else None)

    def _to_intro(self):
        self.topic, self.hover_spot = None, None
        self._draw()

    # which spot
    def _row_spot(self, row):
        it = self.page.table.item(row, 0)
        return it.data(QtCore.Qt.UserRole) if it is not None else None

    def pick(self, r, s):
        self.picked = (r, s)
        self._draw()

    def _clicked(self, row, *_):
        data = self._row_spot(row) if row >= 0 else None
        if data:
            self.pick(*data)

    def spot(self):
        """The spot on show: under the mouse, else clicked, else the first
        isolated row of the table."""
        for cand in (self.hover_spot, self.picked):
            if cand and self._still_listed(cand):
                return cand
        t = self.page.table
        first = None
        for row in range(t.rowCount()):
            d = self._row_spot(row)
            if d and first is None:
                first = d
            if d and d[1].is_isolated:
                return d
        return first

    def _still_listed(self, cand):
        t = self.page.table
        return any(self._row_spot(r) is not None and
                   self._row_spot(r)[1] is cand[1] for r in range(t.rowCount()))

    def _later(self, *_):
        QtCore.QTimer.singleShot(0, self, self._draw)   # not after self is gone

    def showEvent(self, e):
        super().showEvent(e)
        self.page.shown()                # fill the table if it changed while hidden
        self._draw()

    # numbers
    def _params(self, r):
        live = self.s.live
        if live is not None and r is live:
            return self.s.params
        return self.main.results_params or self.main.params

    def _stages(self, r):
        p = self._params(r)
        key = (r.item.key, p)
        if key not in self._cache:
            img = load_item(r.item)
            self._cache = {key: stages(img, p) if img is not None else None}
        return self._cache[key], p

    # drawing
    def _draw(self, *_):
        if not self.isVisible():
            return
        self.view.clear_marks()
        self.profile.getPlotItem().clear()
        got = self.spot()
        fields = {}
        self.empty.setVisible(got is None)
        if got is None:
            self.view.clear_image()
            shown, legend = self.desc.render(self._key(), fields,
                                             self._feature())
            self.legend.show_items("", None, [])
            return
        r, s = got
        st, p = self._stages(r)
        if st is None:
            return
        ap = aperture(st, s, r.info.bg_residual, p)
        half = max(16, p.spot_max_radius + 6)
        if self.topic in ("nn_dist", "is_isolated"):
            # room for the neighbour (up to 60 px away) and the isolation circle
            if np.isfinite(s.nn_dist):
                half = max(half, int(min(s.nn_dist, 60)) + 6)
            half = max(half, int(np.ceil(p.isolation_factor *
                                         s.radius_used)) + 4)
        win = window_at(s.x, s.y, half, st.diff.shape)
        sub = win.cut(st.diff)
        top = float(sub.max()) if sub.size else 1.0
        levels = (0.0, max(top, 1.0))
        self.view.show_image(st.diff, win, levels)
        self.view.where.setText(f"run {r.item.name}   x {s.x}   y {s.y}")
        fields = self._fields(r, s, ap, p)
        self._marks(r, s, ap, p, st)
        self._profile(ap, s)
        shown, legend = self.desc.render(self._key(), fields, self._feature())
        self.legend.show_items(shown, levels, legend)

    def _key(self):
        return self.topic or "intro"

    def _feature(self):
        return self.topic if self.topic in FEATURES else None

    def _aperture_mask(self, ap, shape):
        m = np.zeros(shape, bool)
        h, w = ap.mask.shape
        m[ap.y0:ap.y0 + h, ap.x0:ap.x0 + w] = ap.mask
        return m

    def _marks(self, r, s, ap, p, st):
        v, key = self.view, self.topic
        if key in (None, "spot", "x", "y", "panel", "scope", "iso_only",
                   "info", "save"):
            v.circle(s.x, s.y, s.radius_used + 0.5,
                     ISOLATED if s.is_isolated else AMBER)
            v.points([s.x], [s.y], PHOSPHOR, "+", 14)
            return
        if key == "peak":
            v.box(s.x, s.y, 1, 1, ISOLATED, 2)
            return
        if key == "sum5x5":
            v.box(s.x - 2, s.y - 2, 5, 5, AMBER)
            v.box(s.x, s.y, 1, 1, ISOLATED, 2)
            return
        if key in ("luminosity", "area"):
            v.pixels(self._aperture_mask(ap, st.diff.shape), AMBER, 120)
            v.circle(s.x, s.y, s.radius_used + 0.5, ISOLATED)
            return
        if key == "radius_used":
            v.circle(s.x, s.y, p.spot_max_radius + 0.5, AMBER, 1.2, dashed=True)
            for k in range(1, s.radius_used):
                v.circle(s.x, s.y, k + 0.5, ISOLATED, 0.6, dashed=True)
            v.circle(s.x, s.y, s.radius_used + 0.5, ISOLATED)
            return
        if key == "radial_sigma":
            v.points([ap.gx], [ap.gy], PHOSPHOR, "+", 14)
            v.circle(ap.gx, ap.gy, s.radial_sigma, ISOLATED)
            v.circle(s.x, s.y, s.radius_used + 0.5, AMBER, 1.0, dashed=True)
            return
        if key == "concentration":
            core = np.zeros(st.diff.shape, bool)
            ly, lx = np.nonzero(ap.mask)
            inner = (ap.dx * ap.dx + ap.dy * ap.dy) <= 4
            core[ly[inner] + ap.y0, lx[inner] + ap.x0] = True
            v.pixels(core, AMBER, 150)
            v.points([ap.gx], [ap.gy], PHOSPHOR, "+", 14)
            v.circle(s.x, s.y, s.radius_used + 0.5, ISOLATED)
            return
        if key == "eccentricity":
            v.circle(s.x, s.y, s.radius_used + 0.5, ISOLATED, 1.0, dashed=True)
            self._ellipse(ap)
            return
        if key == "profile_slope":
            v.points([ap.gx], [ap.gy], PHOSPHOR, "+", 14)
            v.circle(s.x, s.y, s.radius_used + 0.5, ISOLATED)
            return
        if key in ("nn_dist", "is_isolated"):
            v.circle(s.x, s.y, s.radius_used + 0.5, ISOLATED)
            if key == "is_isolated":
                v.circle(s.x, s.y, p.isolation_factor * s.radius_used,
                         ISOLATED if s.is_isolated else AMBER, 1.2, dashed=True)
            others = [o for o in r.spots if o is not s]
            if others:
                nn = min(others, key=lambda o: (o.x - s.x) ** 2 + (o.y - s.y) ** 2)
                v.points([nn.x], [nn.y], RED, "o", 14)
                v.line(s.x, s.y, nn.x, nn.y, RED, 1.6)

    def _ellipse(self, ap):
        """The 2σ ellipse of the spot's light, from its second moments."""
        lam, vec = second_moments(ap)          # what eccentricity() uses
        lam = np.clip(lam, 0, None)
        t = np.linspace(0, 2 * np.pi, 90)
        pts = vec @ (2 * np.sqrt(lam)[:, None] * np.stack([np.cos(t), np.sin(t)]))
        path = QtGui.QPainterPath()
        path.addPolygon(QtGui.QPolygonF([QtCore.QPointF(ap.gx + 0.5 + a,
                                                        ap.gy + 0.5 + b)
                                         for a, b in zip(*pts)]))
        item = QtWidgets.QGraphicsPathItem(path)
        pen = QtGui.QPen(QtGui.QColor(AMBER), 1.8)
        pen.setCosmetic(True)
        item.setPen(pen)
        self.view._add(item)
        # the long axis
        a = vec[:, 0] * 2 * np.sqrt(lam[0])
        self.view.line(ap.gx - a[0], ap.gy - a[1], ap.gx + a[0], ap.gy + a[1],
                       AMBER, 1.2)

    def _profile(self, ap, s):
        p = self.profile.getPlotItem()
        r, y, k, c = profile_fit(ap)           # what profile_slope() uses
        if len(r) < 1:
            return
        p.addItem(pg.ScatterPlotItem(r, y, size=5, pen=None,
                                     brush=pg.mkBrush(PHOSPHOR)))
        key = self.topic
        if len(r) >= 3:
            xs = np.array([0, r.max()])
            p.addItem(pg.PlotDataItem(xs, k * xs + c, pen=pg.mkPen(
                AMBER, width=2.2 if key == "profile_slope" else 1.2)))
        if key == "radial_sigma":
            p.addItem(pg.InfiniteLine(s.radial_sigma, angle=90, pen=pg.mkPen(
                ISOLATED, width=1.4)))
        if key == "concentration":
            p.addItem(pg.InfiniteLine(2.0, angle=90, pen=pg.mkPen(
                AMBER, width=1.4, style=QtCore.Qt.DashLine)))

    def _fields(self, r, s, ap, p):
        f = {
            "run": r.item.name, "x": str(s.x), "y": str(s.y),
            "peak": f"{s.peak:.1f}", "sum5x5": f"{s.sum5x5:.0f}",
            "spread": f"{s.sum5x5 / s.peak:.1f}" if s.peak > 0 else "–",
            "luminosity": f"{s.luminosity:.0f}",
            "radius_used": str(s.radius_used), "area": str(s.area),
            "radial_sigma": f"{s.radial_sigma:.2f}",
            "concentration": f"{s.concentration:.3f}",
            "concentration_pct": f"{100 * s.concentration:.0f}",
            "eccentricity": f"{s.eccentricity:.3f}",
            "profile_slope": f"{s.profile_slope:.3f}",
            "nn_dist": f"{s.nn_dist:.1f}" if np.isfinite(s.nn_dist) else "∞",
            "is_isolated": "isolated" if s.is_isolated else "crowded",
            "iso_r": f"{p.isolation_factor * s.radius_used:.3g}",
            "isolation_factor": f"{p.isolation_factor:g}",
            "spot_max_radius": str(p.spot_max_radius),
            "plateau_pct": f"{100 * p.plateau_frac:g}",
            "bg_res": f"{ap.bg_res:.2f}",
            "gx": f"{ap.gx:.1f}", "gy": f"{ap.gy:.1f}",
            "core_light": f"{float(ap.w[(ap.dx ** 2 + ap.dy ** 2) <= 4].sum()):.0f}",
            "total_light": f"{float(ap.wsum):.0f}",
            "n_rows": str(self.page.table.rowCount()),
            "scope": self.page.scope.currentText(),
            "iso_only": "on" if self.page.iso_only.isChecked() else "off",
        }
        if s.profile_slope:
            f["decay_px"] = f"{-1 / s.profile_slope:.2f}" \
                if s.profile_slope < 0 else "–"
        # the eccentricity's two axes
        w, dx, dy, ws = ap.w, ap.dx, ap.dy, ap.wsum
        cxx, cyy = (w * dx * dx).sum() / ws, (w * dy * dy).sum() / ws
        cxy = (w * dx * dy).sum() / ws
        tr, det = cxx + cyy, cxx * cyy - cxy * cxy
        disc = max(tr * tr / 4 - det, 0.0)
        l1, l2 = tr / 2 + np.sqrt(disc), tr / 2 - np.sqrt(disc)
        f["axis_long"] = f"{np.sqrt(max(l1, 0)):.2f}"
        f["axis_short"] = f"{np.sqrt(max(l2, 0)):.2f}"
        # the aperture's growth, ring by ring
        rows, prev = [], 0.0
        for k in range(1, p.spot_max_radius + 1):
            m = ap.r2 <= k * k
            lum = float(ap.sub[m].sum() - ap.bg_res * m.sum())
            gain = (f"+{100 * (lum - prev) / prev:.1f} %" if prev > 0 else "")
            mark = "  ← stops here" if k == s.radius_used else ""
            rows.append(f"- radius {k} px: light {lum:.0f} {gain}{mark}")
            prev = lum
            if k >= s.radius_used + 1:
                break
        f["growth"] = "\n".join(rows)
        return f
