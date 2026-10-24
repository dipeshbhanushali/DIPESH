"""pca: all shape and brightness features at once."""

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from ...clustering_recognition import (ellipse_points, pca, separation_score,
                                       spot_matrix)
from ..theme import MUTED, PANEL, PHOSPHOR, RULE, TEXT, muted, scope_plot
from .base import (FEATURE_LABELS, LOG_BY_DEFAULT, Page, add_legend, combo,
                   empty_overlay, form, labelled, qcolor, side_column)


class PcaPage(Page):
    title = "pca"
    hint = "Every spot feature at once — what separates the datasets"
    DEFAULT = ("luminosity", "radial_sigma", "peak", "concentration",
               "eccentricity", "profile_slope")

    def __init__(self, session):
        super().__init__(session)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(8, 8, 0, 8)
        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.scatter = scope_plot()
        self.loads = scope_plot(ylabel="loading")
        split.addWidget(self.scatter)
        split.addWidget(self.loads)
        split.setSizes([600, 220])
        row.addWidget(split, 1)
        self.empty = empty_overlay(self.scatter, "Run all to fill this.\nPCA "
                                   "needs at least a few isolated spots.")

        side, lay = side_column()
        f = form(lay, "features")
        self.checks = {}
        for k, v in FEATURE_LABELS.items():
            c = QtWidgets.QCheckBox(v)
            c.setChecked(k in self.DEFAULT)
            c.toggled.connect(self.mark)
            self.checks[k] = c
            f.addRow(c)
        g = form(lay, "options")
        self.logf = QtWidgets.QCheckBox("log brightness")
        self.logf.setChecked(True)
        self.logf.setToolTip("Log luminosity, peak and 5x5 sum first. They "
                             "span decades; logging lets PCA see their shape "
                             "rather than their tail")
        g.addRow(self.logf)
        self.iso = QtWidgets.QCheckBox("isolated spots only")
        self.iso.setChecked(True)
        g.addRow(self.iso)
        self.ell = QtWidgets.QCheckBox("2σ ellipses")
        self.ell.setChecked(True)
        g.addRow(self.ell)
        self.axes = combo()
        self.axes.addItems(["PC1 vs PC2", "PC1 vs PC3", "PC2 vs PC3"])
        g.addRow(labelled(self.axes, "axes"))
        self.stats = QtWidgets.QLabel("")
        self.stats.setWordWrap(True)
        self.stats.setTextFormat(QtCore.Qt.RichText)
        lay.addWidget(self.stats)
        lay.addStretch(1)
        row.addWidget(side)

        for w in (self.logf, self.iso, self.ell):
            w.toggled.connect(self.mark)
        self.axes.currentIndexChanged.connect(self.mark)
        session.resultsChanged.connect(self.mark)
        session.datasetsChanged.connect(self.mark)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty.setGeometry(self.scatter.rect())

    def refresh(self):
        sp, lp = self.scatter.getPlotItem(), self.loads.getPlotItem()
        sp.clear()
        lp.clear()
        if sp.legend:
            sp.legend.scene().removeItem(sp.legend)
            sp.legend = None
        self.stats.setText("")
        feats = [k for k, c in self.checks.items() if c.isChecked()]
        logs = LOG_BY_DEFAULT if self.logf.isChecked() else set()
        blocks = []
        for ds in self.s.datasets:
            spots = [s for r in ds.done() for s in r.spots]
            X = spot_matrix(spots, feats, logs, self.iso.isChecked())
            if len(X):
                blocks.append((ds, X))
        n = sum(len(X) for _, X in blocks)
        ok = len(feats) >= 2 and n >= max(5, len(feats) + 1)
        self.empty.setVisible(not ok)
        if not ok:
            if blocks and len(feats) < 2:
                self.empty.setText("Pick at least two features.")
            return

        scores, ev, load = pca(np.vstack([X for _, X in blocks]))
        i, j = {"PC1 vs PC2": (0, 1), "PC1 vs PC3": (0, 2),
                "PC2 vs PC3": (1, 2)}[self.axes.currentText()]
        j = min(j, scores.shape[1] - 1)
        add_legend(sp)
        start, pc1 = 0, []
        for ds, X in blocks:
            sc = scores[start:start + len(X)]
            start += len(X)
            pc1.append((ds.name, sc[:, 0]))
            sp.addItem(pg.ScatterPlotItem(
                sc[:, i], sc[:, j], symbol=ds.symbol, size=7,
                pen=pg.mkPen(PANEL, width=0.6), brush=qcolor(ds.colour, 200),
                name=f"{ds.name}  (n={len(X)})"))
            if self.ell.isChecked():
                pts = ellipse_points(sc[:, i], sc[:, j])
                if pts is not None:
                    path = QtGui.QPainterPath()
                    path.addPolygon(QtGui.QPolygonF(
                        [QtCore.QPointF(a, b) for a, b in zip(*pts)]))
                    item = QtWidgets.QGraphicsPathItem(path)
                    pen = QtGui.QPen(QtGui.QColor(ds.colour), 1.6)
                    pen.setCosmetic(True)
                    item.setPen(pen)
                    item.setBrush(QtGui.QBrush(qcolor(ds.colour, 28)))
                    sp.addItem(item)
        sp.setLabel("bottom", f"PC{i + 1}  ({ev[i]:.0%} of variance)",
                    color=MUTED)
        sp.setLabel("left", f"PC{j + 1}  ({ev[j]:.0%} of variance)",
                    color=MUTED)

        x = np.arange(len(feats))
        lp.addItem(pg.BarGraphItem(x=x - 0.18, height=load[i], width=0.34,
                                   brush=qcolor(TEXT, 210), pen=None))
        lp.addItem(pg.BarGraphItem(x=x + 0.18, height=load[j], width=0.34,
                                   brush=qcolor(MUTED, 170), pen=None))
        lp.setLabel("left", f"loading  (light PC{i + 1}, dark PC{j + 1})",
                    color=MUTED)
        lp.addLine(y=0, pen=pg.mkPen(RULE))
        lp.getAxis("bottom").setTicks([[(k, FEATURE_LABELS[f].replace(
            "nearest-neighbour distance", "nn dist")) for k, f in
            enumerate(feats)]])

        lines = [f"<p style='color:{muted()}; margin-bottom:2px'>variance "
                 f"explained</p><p style='margin-top:0'>" +
                 "<br>".join(f"PC{k + 1}  {v:5.1%}" for k, v in
                             enumerate(ev[:4])) + "</p>"]
        if len(pc1) == 2:
            (na, a), (nb, b) = pc1
            sep = separation_score(a, b)
            lines.insert(0, f"<p style='color:{PHOSPHOR}; font-size:20pt; "
                         f"margin:0'>{sep:.2f}</p><p style='color:{muted()}; "
                         f"margin-top:0'>PC1 separation, {na} vs {nb}</p>")
        top = np.argsort(-np.abs(load[0]))[:3]
        lines.append(f"<p style='color:{muted()}; margin-bottom:2px'>PC1 is "
                     f"mostly</p><p style='margin-top:0'>" + "<br>".join(
                         f"{'+' if load[0][k] > 0 else '−'} "
                         f"{FEATURE_LABELS[feats[k]]}" for k in top) + "</p>")
        self.stats.setText("".join(lines))
