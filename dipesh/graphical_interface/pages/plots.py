"""plots: any run quantity against any Batman parameter, averaged, fitted."""

import csv

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from ...results import RUN_METRICS, average_xy, fit_curve
from ..theme import MUTED, PANEL, muted, scope_plot
from .base import (Page, add_legend, combo, empty_overlay, form, labelled,
                   qcolor, side_column)


class PlotsPage(Page):
    title = "plots"
    hint = "Any run quantity against any Batman parameter, averaged and fitted"

    def __init__(self, session):
        super().__init__(session)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(8, 8, 0, 8)
        self.plot = scope_plot()
        row.addWidget(self.plot, 1)
        self.empty = empty_overlay(self.plot, "Run all to fill this.\nPlot "
                                   "counts, luminosity or pickup against any "
                                   "Batman parameter.")

        side, lay = side_column()
        f = form(lay, "axes")
        self.x = combo()
        self.y = combo()
        self.x.setMaxVisibleItems(25)
        self.y.setMaxVisibleItems(25)
        f.addRow(labelled(self.x, "x axis"))
        f.addRow(labelled(self.y, "y axis"))
        self.logx = QtWidgets.QCheckBox("log x")
        self.logy = QtWidgets.QCheckBox("log y")
        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.logx)
        h.addWidget(self.logy)
        f.addRow(h)
        self.varying = QtWidgets.QCheckBox("only parameters that change")
        self.varying.setChecked(True)
        f.addRow(self.varying)

        g = form(lay, "repeats")
        self.avg = QtWidgets.QCheckBox("average runs at the same x")
        self.avg.setChecked(True)
        g.addRow(self.avg)
        self.err = combo()
        self.err.addItems(["standard error", "standard deviation"])
        g.addRow(labelled(self.err, "error shown"))
        self.bars = QtWidgets.QCheckBox("error bars")
        g.addRow(self.bars)
        self.raw = QtWidgets.QCheckBox("raw points behind")
        self.raw.setChecked(True)
        g.addRow(self.raw)
        self.line = QtWidgets.QCheckBox("join averaged points")
        g.addRow(self.line)

        k = form(lay, "fit")
        self.fit = combo()
        self.fit.addItems(["none", "linear", "quadratic", "exponential"])
        k.addRow(labelled(self.fit, "model"))
        self.fit_text = QtWidgets.QLabel("")
        self.fit_text.setWordWrap(True)
        self.fit_text.setTextFormat(QtCore.Qt.RichText)
        lay.addWidget(self.fit_text)
        lay.addStretch(1)
        save = QtWidgets.QPushButton("Save plot data…")
        save.setToolTip("The numbers behind this plot, as CSV")
        save.clicked.connect(self._save)
        lay.addWidget(save)
        row.addWidget(side)

        self._x_touched = False
        self.x.activated.connect(lambda *_: setattr(self, "_x_touched", True))
        for w in (self.x, self.y, self.err, self.fit):
            w.currentIndexChanged.connect(self.mark)
        for w in (self.logx, self.logy, self.avg, self.bars, self.raw,
                  self.line):
            w.toggled.connect(self.mark)
        self.varying.toggled.connect(lambda *_: (self._fill_axes(),
                                                 self.mark()))
        session.resultsChanged.connect(lambda *_: (self._fill_axes(),
                                                   self.mark()))
        session.datasetsChanged.connect(self.mark)
        self._series = []

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty.setGeometry(self.plot.rect())

    def _fill_axes(self):
        results = [r for d in self.s.datasets for r in d.done()]
        keys = sorted({k for r in results for k in r.batman})
        if self.varying.isChecked():
            keys = [k for k in keys
                    if len({r.batman.get(k) for r in results}) > 1]
        pick = sorted({k for r in results for k in r.pickup
                       if not k.endswith("_delay_us")})

        def refill(box, entries, default):
            cur = box.currentData()
            box.blockSignals(True)
            box.clear()
            for data, label in entries:
                box.addItem(label, data)
            idx = box.findData(cur if cur is not None else default)
            box.setCurrentIndex(max(0, idx))
            box.blockSignals(False)

        x_entries = [("run_number", "run number")] + [(k, k) for k in keys]
        if not self._x_touched:
            # a scan variable is present in most runs and takes few distinct
            # values that repeat; pick the one that looks most like that
            def scan_score(k):
                vals = [r.batman[k] for r in results if k in r.batman]
                if len(vals) < 2:
                    return -1
                return (len(vals) / len(results)) * (1 - len(set(vals)) /
                                                     len(vals))
            best = max(keys, key=scan_score, default=None)
            if best is not None and scan_score(best) > 0:
                self.x.blockSignals(True)
                self.x.clear()
                self.x.blockSignals(False)
                refill(self.x, x_entries, best)
            else:
                refill(self.x, x_entries, "run_number")
        else:
            refill(self.x, x_entries, "run_number")
        y_entries = list(RUN_METRICS.items()) + [(k, k) for k in pick]
        refill(self.y, y_entries, "pbar_count")

    def _x_label(self):
        return self.x.currentText()

    def refresh(self):
        if self.x.count() == 0:
            self._fill_axes()
        p = self.plot.getPlotItem()
        p.clear()
        if p.legend:
            p.legend.scene().removeItem(p.legend)
            p.legend = None
        self.fit_text.setText("")
        self._series = []
        xk, yk = self.x.currentData(), self.y.currentData()
        have = any(d.done() for d in self.s.datasets)
        self.empty.setVisible(not have)
        if not have or xk is None or yk is None:
            return
        add_legend(p)
        lx, ly = self.logx.isChecked(), self.logy.isChecked()

        def tf(x, y):
            """Log axes done on the data: pyqtgraph's log mode is not honoured
            by scatter and error-bar items."""
            keep = np.ones(len(x), bool)
            if lx:
                keep &= x > 0
            if ly:
                keep &= y > 0
            x, y = x[keep], y[keep]
            return (np.log10(x) if lx else x), (np.log10(y) if ly else y), keep

        error = "sem" if self.err.currentIndex() == 0 else "std"
        notes = []
        for ds in self.s.datasets:
            rs = ds.done()
            if not rs:
                continue
            xs = np.array([r.metric(xk) for r in rs], float)
            ys = np.array([r.metric(yk) for r in rs], float)
            good = np.isfinite(xs) & np.isfinite(ys)
            xs, ys = xs[good], ys[good]
            if not len(xs):
                continue
            self._series.append((ds.name, xs, ys))
            if self.avg.isChecked():
                xm, ym, ye, ns = average_xy(xs, ys, error=error)
                if self.raw.isChecked() and len(xm) < len(xs):
                    rx, ry, _ = tf(xs, ys)
                    p.addItem(pg.PlotDataItem(
                        rx, ry, pen=None, symbol=ds.symbol, symbolSize=6,
                        symbolPen=None, symbolBrush=qcolor(ds.colour, 70)))
            else:
                xm, ym, ye = xs, ys, np.zeros_like(ys)
            px, py, keep = tf(xm, ym)
            pe = ye[keep]
            if self.bars.isChecked() and np.any(pe > 0) and not ly:
                p.addItem(pg.ErrorBarItem(x=px, y=py, top=pe, bottom=pe,
                                          beam=0, pen=pg.mkPen(ds.colour)))
            p.addItem(pg.PlotDataItem(
                px, py, symbol=ds.symbol, symbolSize=11,
                symbolBrush=ds.colour, symbolPen=pg.mkPen(PANEL, width=1.2),
                pen=pg.mkPen(ds.colour, width=1.5) if self.line.isChecked()
                else None, name=ds.name))
            kind = self.fit.currentText()
            if kind != "none":
                res = fit_curve(xm, ym, ye if np.any(ye > 0) else None, kind)
                if res:
                    fx, fy, _ = tf(res["xfit"], res["yfit"])
                    p.addItem(pg.PlotDataItem(
                        fx, fy, pen=pg.mkPen(ds.colour, width=2,
                                             style=QtCore.Qt.DashLine)))
                    par = ", ".join(f"{n}={v:.4g}" for n, v in
                                    zip("abc", res["params"]))
                    notes.append(f"<p><span style='color:{ds.colour}'>"
                                 f"{ds.name}</span><br>{res['formula']}<br>"
                                 f"{par}<br><span style='color:{muted()}'>R² = "
                                 f"{res['r2']:.3f}</span></p>")
                else:
                    notes.append(f"<p><span style='color:{ds.colour}'>"
                                 f"{ds.name}</span>: needs at least three "
                                 f"distinct x values to fit</p>")
        p.setLabel("bottom", ("log₁₀ " if lx else "") + self._x_label(),
                   color=MUTED)
        p.setLabel("left", ("log₁₀ " if ly else "") + self.y.currentText(),
                   color=MUTED)
        self.fit_text.setText("".join(notes))

    def _save(self):
        if not self._series:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save plot data", "plot_data.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["dataset", self.x.currentData(), self.y.currentData()])
            for name, xs, ys in self._series:
                for a, b in zip(xs, ys):
                    w.writerow([name, a, b])
        self.s.log(f"plot data saved to {path}", "ok")
