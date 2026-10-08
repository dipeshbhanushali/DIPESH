"""histogram: one feature across datasets; separation and best cut."""

import math

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from ...clustering_recognition import best_threshold, separation_score
from ..theme import AMBER, MUTED, PHOSPHOR, scope_plot
from .base import (FEATURE_LABELS, LOG_BY_DEFAULT, Page, add_legend, combo,
                   empty_overlay, form, labelled, qcolor, side_column)


class HistogramPage(Page):
    title = "histogram"
    hint = "One spot feature across datasets, with separation and best cut"

    def __init__(self, session):
        super().__init__(session)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(8, 8, 0, 8)
        self.plot = scope_plot()
        row.addWidget(self.plot, 1)
        self.empty = empty_overlay(self.plot, "Run all to fill this.\nThe "
                                   "histogram uses every counted spot in "
                                   "every dataset.")

        side, lay = side_column()
        f = form(lay, "what to plot")
        self.feature = combo()
        for k, v in FEATURE_LABELS.items():
            self.feature.addItem(v, k)
        f.addRow(labelled(self.feature, "feature"))
        self.logx = QtWidgets.QCheckBox("log scale")
        self.logx.setChecked(True)
        f.addRow("", self.logx)
        self.bins = QtWidgets.QSpinBox()
        self.bins.setRange(5, 200)
        self.bins.setValue(30)
        f.addRow("bins", self.bins)
        self.iso = QtWidgets.QCheckBox("isolated spots only")
        self.iso.setChecked(True)
        self.iso.setToolTip("Crowded spots share light with their neighbours, "
                            "so their luminosity is not a single particle's")
        f.addRow("", self.iso)
        self.norm = QtWidgets.QCheckBox("normalise each dataset")
        self.norm.setChecked(True)
        self.norm.setToolTip("Compare shapes when datasets differ in size")
        f.addRow("", self.norm)

        g = form(lay, "compare two")
        self.a = combo()
        self.b = combo()
        g.addRow(labelled(self.a, "lower dataset"))
        g.addRow(labelled(self.b, "higher dataset"))
        self.cut = QtWidgets.QCheckBox("draw best cut")
        self.cut.setChecked(True)
        g.addRow("", self.cut)
        self.stats = QtWidgets.QLabel("")
        self.stats.setWordWrap(True)
        self.stats.setTextFormat(QtCore.Qt.RichText)
        lay.addWidget(self.stats)
        lay.addStretch(1)
        row.addWidget(side)

        for w in (self.feature, self.a, self.b):
            w.currentIndexChanged.connect(self.mark)
        for w in (self.logx, self.iso, self.norm, self.cut):
            w.toggled.connect(self.mark)
        self.bins.valueChanged.connect(self.mark)
        self.feature.currentIndexChanged.connect(
            lambda *_: self.logx.setChecked(
                self.feature.currentData() in LOG_BY_DEFAULT))
        session.resultsChanged.connect(self.mark)
        session.datasetsChanged.connect(self.mark)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty.setGeometry(self.plot.rect())

    def _values(self, ds):
        feat = self.feature.currentData()
        out = []
        for r in ds.done():
            for s in r.spots:
                if self.iso.isChecked() and not s.is_isolated:
                    continue
                v = float(getattr(s, feat))
                if not math.isfinite(v):
                    continue
                if self.logx.isChecked():
                    if v <= 0:
                        continue
                    v = math.log10(v)
                out.append(v)
        return np.asarray(out)

    def _fill_pairs(self):
        names = [d.name for d in self.s.datasets]
        for box, default in ((self.a, 1), (self.b, 0)):
            cur = box.currentText()
            box.blockSignals(True)
            box.clear()
            box.addItems(names)
            if cur in names:
                box.setCurrentText(cur)
            elif len(names) > default:
                box.setCurrentIndex(default)
            box.blockSignals(False)

    def refresh(self):
        self._fill_pairs()
        p = self.plot.getPlotItem()
        p.clear()
        if p.legend:
            p.legend.scene().removeItem(p.legend)
            p.legend = None
        data = {d.name: (d, self._values(d)) for d in self.s.datasets}
        data = {k: v for k, v in data.items() if len(v[1])}
        self.empty.setVisible(not data)
        self.stats.setText("")
        if not data:
            return
        add_legend(p)
        allv = np.concatenate([v for _, v in data.values()])
        edges = np.linspace(allv.min(), allv.max(), self.bins.value() + 1)
        if edges[-1] == edges[0]:
            edges = edges + np.linspace(-0.5, 0.5, len(edges))
        for name, (ds, v) in data.items():
            h, _ = np.histogram(v, bins=edges)
            if self.norm.isChecked() and h.sum():
                h = h / h.sum()
            p.addItem(pg.PlotDataItem(
                edges, h, stepMode="center", fillLevel=0,
                brush=qcolor(ds.colour, 55), pen=pg.mkPen(ds.colour, width=2),
                name=f"{name}  (n={len(v)})"))
        feat = FEATURE_LABELS[self.feature.currentData()]
        p.setLabel("bottom", f"log₁₀ {feat}" if self.logx.isChecked() else feat,
                   color=MUTED)
        p.setLabel("left", "fraction of spots" if self.norm.isChecked()
                   else "spots", color=MUTED)

        an, bn = self.a.currentText(), self.b.currentText()
        if an in data and bn in data and an != bn:
            va, vb = data[an][1], data[bn][1]
            sep = separation_score(va, vb)
            t, ea, eb, swapped = best_threshold(va, vb)
            lo, hi = (bn, an) if swapped else (an, bn)
            shown = 10 ** t if self.logx.isChecked() else t
            verdict = ("separates cleanly" if sep >= 1.5 else
                       "partly separates" if sep >= 0.5 else "does not separate")
            self.stats.setText(
                f"<p style='color:{PHOSPHOR}; font-size:20pt; margin:0'>"
                f"{sep:.2f}</p><p style='color:{MUTED}; margin-top:0'>"
                f"separation score<br>{feat} {verdict}</p>"
                f"<p>best cut {shown:.4g}<br>{lo} above it: {ea:.0%}<br>"
                f"{hi} below it: {eb:.0%}</p>"
                f"<p style='color:{MUTED}'>score = |Δmean| / (σ₁ + σ₂)</p>")
            if self.cut.isChecked():
                line = pg.InfiniteLine(t, angle=90, pen=pg.mkPen(
                    AMBER, width=1.5, style=QtCore.Qt.DashLine),
                    label=f"cut {shown:.4g}",
                    labelOpts={"color": AMBER, "position": 0.92})
                p.addItem(line)
