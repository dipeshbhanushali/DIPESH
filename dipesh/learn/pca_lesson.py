"""
The pca lesson: how all the features are combined into principal
components, and how to read the scatter and the loadings.

    left    the pca page's scatter and loadings, with what the control under
            the mouse does drawn on them, and a legend
    middle  the loadings and variances as numbers, and the description
    right   the pca page's controls, as on the pca page
"""

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from ..clustering_recognition import pca, separation_score, spot_matrix
from ..graphical_interface.pages.base import (FEATURE_LABELS, LOG_BY_DEFAULT,
                                              qcolor)
from ..graphical_interface.pages.pca import PcaPage
from ..graphical_interface.theme import AMBER, ISOLATED, PHOSPHOR, TEXT
from .description import Description, feature_meaning
from .embedded import embedded, take
from .hover import HoverWatch, map_control
from .image_lesson import Legend

AXES = {"PC1 vs PC2": (0, 1), "PC1 vs PC3": (0, 2), "PC2 vs PC3": (1, 2)}


class PcaLesson(QtWidgets.QWidget):
    title = "pca"
    uses_detection = False

    def __init__(self, main):
        super().__init__()
        self.s = main
        self.topic = None
        self.extra = []
        self.page = embedded(PcaPage)(main, self, self._after)
        split, side = take(self.page)
        self.split = split
        self.empty = self.page.empty

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        fig = QtWidgets.QVBoxLayout()
        fig.addWidget(split, 1)
        self.legend = Legend()
        fig.addWidget(self.legend)
        row.addLayout(fig, 3)

        mid = QtWidgets.QVBoxLayout()
        lab = QtWidgets.QLabel("the numbers")
        lab.setObjectName("heading")
        mid.addWidget(lab)
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(QtCore.Qt.NoFocus)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        for j in (1, 2):
            hh.setSectionResizeMode(j, QtWidgets.QHeaderView.Stretch)
        self.table.setMaximumHeight(300)
        mid.addWidget(self.table)
        self.desc = Description("pca.md")
        self.desc.connect_changed(self._draw)
        mid.addWidget(self.desc, 1)
        row.addLayout(mid, 2)
        row.addWidget(side)

        p = self.page
        self.watch = HoverWatch([side, split], self.hovered)
        for k, c in p.checks.items():
            self.watch.add(c, ("feature", k))
        for w, k in ((p.logf, "logf"), (p.iso, "iso"), (p.ell, "ell"),
                     (p.axes, "axes"), (p.stats, "stats")):
            map_control(self.watch, w, k)
        for box in side.findChildren(QtWidgets.QGroupBox):
            self.watch.add(box, "features" if box.title() == "features"
                           else "options")
        self.watch.add(p.scatter, "scatter")
        self.watch.add(p.loads, "loadings")
        self.idle = QtCore.QTimer(self)
        self.idle.setSingleShot(True)
        self.idle.setInterval(250)
        self.idle.timeout.connect(lambda: self.hovered(None, now=True))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty.setGeometry(self.page.scatter.rect())

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
        self.extra = []
        QtCore.QTimer.singleShot(0, self, self._draw)   # not after self is gone

    # numbers: what the page computes, the same way
    def _compute(self):
        p = self.page
        feats = [k for k, c in p.checks.items() if c.isChecked()]
        logs = LOG_BY_DEFAULT if p.logf.isChecked() else set()
        blocks = []
        for ds in self.s.datasets:
            spots = [s for r in ds.done() for s in r.spots]
            X = spot_matrix(spots, feats, logs, p.iso.isChecked())
            if len(X):
                blocks.append((ds, X))
        n = sum(len(X) for _, X in blocks)
        if len(feats) < 2 or n < max(5, len(feats) + 1):
            return None
        scores, ev, load = pca(np.vstack([X for _, X in blocks]))
        i, j = AXES[p.axes.currentText()]
        j = min(j, scores.shape[1] - 1)
        return dict(feats=feats, blocks=blocks, scores=scores, ev=ev,
                    load=load, i=i, j=j, n=n)

    def _fields(self, c):
        p = self.page
        f = {"n_features": str(sum(ch.isChecked() for ch in p.checks.values())),
             "logf": "on" if p.logf.isChecked() else "off",
             "iso": "on" if p.iso.isChecked() else "off",
             "ell": "on" if p.ell.isChecked() else "off",
             "axes": p.axes.currentText()}
        topic = self.topic
        if isinstance(topic, tuple):
            k = topic[1]
            f["feature"] = FEATURE_LABELS.get(k, k)
            f["feature_meaning"] = feature_meaning(k)
            f["checked"] = "included" if p.checks[k].isChecked() else \
                "not included"
            f["logged"] = ("is" if p.logf.isChecked() and k in LOG_BY_DEFAULT
                           else "is not")
        if c is None:
            return f
        i, j, ev, load, feats = c["i"], c["j"], c["ev"], c["load"], c["feats"]
        f.update({"n": str(c["n"]), "pi": f"PC{i + 1}", "pj": f"PC{j + 1}",
                  "ev_i": f"{ev[i]:.0%}", "ev_j": f"{ev[j]:.0%}",
                  "ev_1": f"{ev[0]:.0%}",
                  "ev_12": f"{ev[0] + (ev[1] if len(ev) > 1 else 0):.0%}",
                  "datasets": ", ".join(f"{ds.name} ({len(X)})"
                                        for ds, X in c["blocks"])})
        top = np.argsort(-np.abs(load[0]))[:3]
        f["pc1_mostly"] = ", ".join(
            f"{'+' if load[0][k] > 0 else '−'} {FEATURE_LABELS[feats[k]]}"
            for k in top)
        if len(c["blocks"]) == 2:
            start = len(c["blocks"][0][1])
            a, b = c["scores"][:start, 0], c["scores"][start:, 0]
            f["pc1_sep"] = f"{separation_score(a, b):.2f}"
            f["pair"] = f"{c['blocks'][0][0].name} and {c['blocks'][1][0].name}"
        else:
            f["pc1_sep"] = "not shown"
            f["pair"] = f"there are {len(c['blocks'])} datasets now"
        if isinstance(topic, tuple):
            if topic[1] in feats:
                k = feats.index(topic[1])
                f["load_i"] = f"{load[i][k]:+.2f}"
                f["load_j"] = f"{load[j][k]:+.2f}"
            else:
                f["load_i"] = f["load_j"] = "no loading"
        return f

    def _table(self, c):
        t = self.table
        if c is None:
            t.setRowCount(0)
            return
        i, j, load, feats, ev = c["i"], c["j"], c["load"], c["feats"], c["ev"]
        t.setHorizontalHeaderLabels(["", f"PC{i + 1} loading",
                                     f"PC{j + 1} loading"])
        rows = ([(FEATURE_LABELS[f], f"{load[i][k]:+.2f}", f"{load[j][k]:+.2f}",
                  f) for k, f in enumerate(feats)] +
                [("variance explained", f"{ev[i]:.0%}", f"{ev[j]:.0%}", "ev")])
        t.setRowCount(len(rows))
        topic = self.topic
        for r, (name, a, b, key) in enumerate(rows):
            hot = ((isinstance(topic, tuple) and topic[1] == key) or
                   (topic in ("axes", "stats", "loadings") and key == "ev"))
            for col, text in enumerate((name, a, b)):
                it = QtWidgets.QTableWidgetItem(text)
                if col:
                    it.setTextAlignment(QtCore.Qt.AlignRight |
                                        QtCore.Qt.AlignVCenter)
                it.setBackground(qcolor(PHOSPHOR, 45) if hot else QtGui.QBrush())
                it.setForeground(QtGui.QColor(PHOSPHOR if hot else TEXT))
                t.setItem(r, col, it)
        t.resizeRowsToContents()

    # drawing
    def _clear_extra(self):
        for plot, it in self.extra:
            plot.removeItem(it)
        self.extra = []

    def _add(self, plot, item):
        plot.addItem(item)
        self.extra.append((plot, item))

    def _arrow(self, sp, k, c, scale, colour, width=2.0, label=True):
        i, j = c["i"], c["j"]
        x, y = c["load"][i][k] * scale, c["load"][j][k] * scale
        self._add(sp, pg.PlotDataItem([0, x], [0, y], pen=pg.mkPen(
            colour, width=width)))
        self._add(sp, pg.ScatterPlotItem([x], [y], symbol="o", size=7,
                                         pen=None, brush=pg.mkBrush(colour)))
        if label:
            t = pg.TextItem(FEATURE_LABELS[c["feats"][k]], color=colour,
                            anchor=(0.5, 1.2))
            t.setPos(x, y)
            self._add(sp, t)

    def _draw(self, *_):
        if not self.isVisible():
            return
        self._clear_extra()
        c = self._compute()
        f = self._fields(c)
        self._table(c)
        topic = self.topic
        key = ("feature" if isinstance(topic, tuple) else topic) or "intro"
        feature = topic[1] if isinstance(topic, tuple) else None
        shown, legend = self.desc.render(key, f, feature)
        self.legend.show_items("", None, legend)
        if c is None:
            return
        sp = self.page.scatter.getPlotItem()
        lp = self.page.loads.getPlotItem()
        sc = c["scores"]
        scale = 0.85 * float(np.abs(sc[:, [c["i"], c["j"]]]).max() or 1.0)
        if isinstance(topic, tuple) and topic[1] in c["feats"]:
            k = c["feats"].index(topic[1])
            self._arrow(sp, k, c, scale, AMBER, 2.4)
            for dx, h in ((-0.18, c["load"][c["i"]][k]),
                          (0.18, c["load"][c["j"]][k])):
                r = QtWidgets.QGraphicsRectItem(k + dx - 0.19, min(0, h),
                                                0.38, abs(h))
                pen = QtGui.QPen(QtGui.QColor(AMBER), 2)
                pen.setCosmetic(True)
                r.setPen(pen)
                self._add(lp, r)
        elif topic in ("axes", "scatter"):
            for k in range(len(c["feats"])):
                self._arrow(sp, k, c, scale, AMBER, 1.6)
            self._add(sp, pg.InfiniteLine(0, angle=90, pen=pg.mkPen(
                ISOLATED, width=0.8, style=QtCore.Qt.DotLine)))
            self._add(sp, pg.InfiniteLine(0, angle=0, pen=pg.mkPen(
                ISOLATED, width=0.8, style=QtCore.Qt.DotLine)))
        elif topic in ("ell", "stats"):
            start = 0
            for ds, X in c["blocks"]:
                part = sc[start:start + len(X)]
                start += len(X)
                mx, my = part[:, c["i"]].mean(), part[:, c["j"]].mean()
                self._add(sp, pg.ScatterPlotItem(
                    [mx], [my], symbol="+", size=26,
                    pen=pg.mkPen(ds.colour, width=3)))
                if topic == "stats" and c["i"] == 0:
                    self._add(sp, pg.InfiniteLine(mx, angle=90, pen=pg.mkPen(
                        ds.colour, width=1.8, style=QtCore.Qt.DashLine)))
        elif topic == "loadings":
            top = np.argsort(-np.abs(c["load"][c["i"]]))[:3]
            for k in top:
                h = c["load"][c["i"]][k]
                r = QtWidgets.QGraphicsRectItem(k - 0.37, min(0, h), 0.38, abs(h))
                pen = QtGui.QPen(QtGui.QColor(AMBER), 2)
                pen.setCosmetic(True)
                r.setPen(pen)
                self._add(lp, r)
