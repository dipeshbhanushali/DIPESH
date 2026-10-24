"""
The histogram lesson: how one feature is compared across datasets, and how
the separation score and the best cut are computed.

    left    the histogram page's plot, with what the control under the mouse
            does drawn on it, and a legend
    middle  the numbers behind the score and the cut, and the description
    right   the histogram page's controls, as on the histogram page
"""

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from ...clustering_recognition import best_threshold, separation_score
from ..pages.base import FEATURE_LABELS, qcolor
from ..pages.histogram import HistogramPage
from ..theme import ISOLATED, PHOSPHOR, TEXT
from .description import Description, feature_meaning
from .embedded import embedded, take
from .hover import HoverWatch, map_control
from .image_lesson import Legend

ROWS = ["n", "mean", "σ", "|Δmean|", "σ₁ + σ₂", "separation score",
        "best cut", "lower above the cut", "higher below the cut"]

# the rows of the table each topic is about
HIGHLIGHT = {
    "a": ["n", "mean", "σ"], "b": ["n", "mean", "σ"],
    "stats": ["|Δmean|", "σ₁ + σ₂", "separation score"],
    "cut": ["best cut", "lower above the cut", "higher below the cut"],
    "iso": ["n"], "norm": ["n"],
}


class HistogramLesson(QtWidgets.QWidget):
    title = "histogram"
    uses_detection = False

    def __init__(self, main):
        super().__init__()
        self.s = main
        self.topic = None
        self.extra = []
        self.page = embedded(HistogramPage)(main, self, self._after)
        plot, side = take(self.page)
        self.plot = plot
        self.empty = self.page.empty

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        fig = QtWidgets.QVBoxLayout()
        fig.addWidget(plot, 1)
        self.legend = Legend()
        fig.addWidget(self.legend)
        row.addLayout(fig, 3)

        mid = QtWidgets.QVBoxLayout()
        lab = QtWidgets.QLabel("the numbers")
        lab.setObjectName("heading")
        mid.addWidget(lab)
        self.table = QtWidgets.QTableWidget(len(ROWS), 3)
        self.table.setHorizontalHeaderLabels(["", "lower", "higher"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(QtCore.Qt.NoFocus)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        for j in (1, 2):
            hh.setSectionResizeMode(j, QtWidgets.QHeaderView.Stretch)
        for i, name in enumerate(ROWS):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(name))
            for j in (1, 2):
                it = QtWidgets.QTableWidgetItem("–")
                it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(i, j, it)
        self.table.resizeRowsToContents()
        self.table.setFixedHeight(self.table.horizontalHeader().sizeHint()
                                  .height() + sum(self.table.rowHeight(i)
                                                  for i in range(len(ROWS))) + 4)
        mid.addWidget(self.table)
        self.desc = Description("histogram.md")
        self.desc.connect_changed(self._draw)
        mid.addWidget(self.desc, 1)
        row.addLayout(mid, 2)
        row.addWidget(side)

        pg_ = self.page
        self.watch = HoverWatch([side, plot], self.hovered)
        for w, k in ((pg_.feature, "feature"), (pg_.logx, "logx"),
                     (pg_.bins, "bins"), (pg_.iso, "iso"), (pg_.norm, "norm"),
                     (pg_.a, "a"), (pg_.b, "b"), (pg_.cut, "cut"),
                     (pg_.stats, "stats")):
            map_control(self.watch, w, k)
        for box in side.findChildren(QtWidgets.QGroupBox):
            self.watch.add(box, "what" if box.title() == "what to plot"
                           else "compare")
        self.watch.add(plot, "plot")
        self.idle = QtCore.QTimer(self)
        self.idle.setSingleShot(True)
        self.idle.setInterval(250)
        self.idle.timeout.connect(lambda: self.hovered(None, now=True))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty.setGeometry(self.plot.rect())

    def showEvent(self, e):
        super().showEvent(e)
        self.page.shown()
        self._draw()

    def hovered(self, key, now=False):
        if not self.isVisible():
            return
        if key is None and not now:
            self.idle.start()
            return
        self.idle.stop()
        if key != self.topic:
            self.topic = key
            self._draw()

    def _after(self):
        self.extra = []                  # the page's redraw cleared them
        QtCore.QTimer.singleShot(0, self, self._draw)   # not after self is gone

    # numbers
    def _data(self):
        """What the page plots: {name: (dataset, values)}, the bin edges,
        and the two compared, as the page computes them."""
        pg_ = self.page
        data = {d.name: (d, pg_._values(d)) for d in self.s.datasets}
        data = {k: v for k, v in data.items() if len(v[1])}
        if not data:
            return data, None, None
        allv = np.concatenate([v for _, v in data.values()])
        edges = np.linspace(allv.min(), allv.max(), pg_.bins.value() + 1)
        if edges[-1] == edges[0]:
            edges = edges + np.linspace(-0.5, 0.5, len(edges))
        an, bn = pg_.a.currentText(), pg_.b.currentText()
        pair = ((an, bn) if an in data and bn in data and an != bn else None)
        return data, edges, pair

    def _fields(self, data, edges, pair):
        pg_ = self.page
        feat = pg_.feature.currentData()
        log = pg_.logx.isChecked()
        f = {
            "feature": FEATURE_LABELS.get(feat, feat or ""),
            "feature_meaning": feature_meaning(feat) if feat else "",
            "log": "on" if log else "off",
            "unit": "log₁₀ " if log else "",
            "bins": str(pg_.bins.value()),
            "iso": "on" if pg_.iso.isChecked() else "off",
            "norm": "on" if pg_.norm.isChecked() else "off",
            "n_datasets": str(len(data)),
            "datasets": ", ".join(f"{k} ({len(v[1])})" for k, v in data.items()),
        }
        if edges is not None:
            f["bin_width"] = f"{edges[1] - edges[0]:.3g}"
            f["lo_edge"], f["hi_edge"] = f"{edges[0]:.3g}", f"{edges[-1]:.3g}"
        if pair:
            an, bn = pair
            va, vb = data[an][1], data[bn][1]
            sep = separation_score(va, vb)
            t, ea, eb, swapped = best_threshold(va, vb)
            lo, hi = (bn, an) if swapped else (an, bn)
            vlo, vhi = (vb, va) if swapped else (va, vb)
            f.update({
                "a": an, "b": bn, "lo": lo, "hi": hi,
                "n_lo": str(len(vlo)), "n_hi": str(len(vhi)),
                "mean_lo": f"{vlo.mean():.3g}", "mean_hi": f"{vhi.mean():.3g}",
                "sd_lo": f"{vlo.std():.3g}", "sd_hi": f"{vhi.std():.3g}",
                "dmean": f"{abs(vhi.mean() - vlo.mean()):.3g}",
                "sdsum": f"{vlo.std() + vhi.std():.3g}",
                "sep": f"{sep:.2f}",
                "verdict": ("separates cleanly" if sep >= 1.5 else
                            "partly separates" if sep >= 0.5 else
                            "does not separate"),
                "cut": f"{t:.3g}",
                "cut_shown": f"{10 ** t if log else t:.4g}",
                "lo_above": f"{ea:.0%}", "hi_below": f"{eb:.0%}",
                "swapped": ("yes" if swapped else "no"),
            })
        return f

    def _table(self, f, pair):
        vals = {
            "n": (f.get("n_lo"), f.get("n_hi")),
            "mean": (f.get("mean_lo"), f.get("mean_hi")),
            "σ": (f.get("sd_lo"), f.get("sd_hi")),
            "|Δmean|": (f.get("dmean"), None),
            "σ₁ + σ₂": (f.get("sdsum"), None),
            "separation score": (f.get("sep"), None),
            "best cut": (f.get("cut_shown"), None),
            "lower above the cut": (f.get("lo_above"), None),
            "higher below the cut": (None, f.get("hi_below")),
        }
        self.table.setHorizontalHeaderLabels(
            ["", f["lo"] if pair else "lower", f["hi"] if pair else "higher"])
        hot = set(HIGHLIGHT.get(self.topic, []))
        for i, name in enumerate(ROWS):
            a, b = vals[name]
            self.table.item(i, 1).setText(a or "")
            self.table.item(i, 2).setText(b or "")
            for j in range(3):
                it = self.table.item(i, j)
                it.setBackground(qcolor(PHOSPHOR, 45) if name in hot
                                 else QtGui.QBrush())
                it.setForeground(QtGui.QColor(PHOSPHOR if name in hot
                                              else TEXT))

    # drawing
    def _clear_extra(self):
        p = self.plot.getPlotItem()
        for it in self.extra:
            p.removeItem(it)
        self.extra = []

    def _add(self, item):
        self.plot.getPlotItem().addItem(item)
        self.extra.append(item)

    def _draw(self, *_):
        if not self.isVisible():
            return
        self._clear_extra()
        data, edges, pair = self._data()
        f = self._fields(data, edges, pair)
        self._table(f, pair)
        shown, legend = self.desc.render(
            self.topic or "intro", f,
            self.page.feature.currentData() if self.topic == "feature" else None)
        self.legend.show_items("", None, legend)
        if edges is None:
            return
        key = self.topic
        if key == "bins":
            for e in edges:
                self._add(pg.InfiniteLine(e, angle=90, pen=pg.mkPen(
                    ISOLATED, width=0.8, style=QtCore.Qt.DashLine)))
        if pair is None:
            return
        an, bn = pair
        lo, hi = (f["lo"], f["hi"])
        if key in ("a", "b", "stats"):
            for name in (lo, hi):
                ds, v = data[name]
                m, sd = float(v.mean()), float(v.std())
                band = pg.LinearRegionItem((m - sd, m + sd), movable=False,
                                           brush=qcolor(ds.colour, 40),
                                           pen=pg.mkPen(None))
                self._add(band)
                self._add(pg.InfiniteLine(m, angle=90, pen=pg.mkPen(
                    ds.colour, width=2.2, style=QtCore.Qt.DashLine)))
        if key == "cut":
            t = best_threshold(data[an][1], data[bn][1])[0]
            norm = self.page.norm.isChecked()
            for name, side in ((lo, "above"), (hi, "below")):
                # the misidentified spots themselves, in the page's bins
                ds, v = data[name]
                wrong = v[v > t] if side == "above" else v[v <= t]
                hh, _ = np.histogram(wrong, bins=edges)
                if norm and len(v):
                    hh = hh / len(v)
                self._add(pg.PlotDataItem(edges, hh, stepMode="center",
                                          fillLevel=0,
                                          brush=qcolor(ds.colour, 170),
                                          pen=pg.mkPen(ds.colour, width=1)))
