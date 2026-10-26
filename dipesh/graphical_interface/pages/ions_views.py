"""
The views of the Ions page. Each shows what ion_analysis computed for the
dataset selected on the page (page.current()); none computes physics
itself (histogram bins and plot ranges are only drawing).

    ReleaseView      the release video frame by frame: the frame or the frame
                     with the background taken off, the single ions, the
                     region and pile-up disc (drag them), the count of every
                     frame, frames left out
    CalibrationView  the light of every single ion and the SIS
    PileupView       the ions in the pile-up disc, frame by frame, per method
    ErrorsView       the dataset's error table
    DecayView        N0 exp(-t/tau) over chosen datasets; tau from two
    ExportView       CSV and JSON of everything
"""

import dataclasses

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from ...ion_analysis import (ErrorComponent, ErrorTable, evaluate, fit_decay,
                             frame_view, read_frame, report, two_point_tau)
from ...ion_analysis.datasets import frame_number
from ...ion_analysis.decay import PROPAGATIONS
from ...ion_analysis.errors import COMBINE, GROUPS, KINDS, PER_FRAME, SPREADS
from ..theme import AMBER, ISOLATED, MUTED, PHOSPHOR, SERIES, TEXT, scope_plot
from .base import combo, empty_overlay, labelled, qcolor
from .image import phosphor_map


def _method_names(result):
    return result.method_names() if result is not None else []


class ReleaseView(QtWidgets.QWidget):
    title = "release"

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.items = []
        self._key = None
        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(0, 6, 0, 0)

        row = QtWidgets.QHBoxLayout()
        self.prev = QtWidgets.QPushButton("◀")
        self.next = QtWidgets.QPushButton("▶")
        for b in (self.prev, self.next):
            b.setFixedWidth(40)
        self.frame = QtWidgets.QSpinBox()
        self.frame.setKeyboardTracking(False)
        self.frame.setPrefix("frame ")
        self.subtracted = QtWidgets.QCheckBox("background taken off")
        self.subtracted.setChecked(True)
        self.left_out = QtWidgets.QCheckBox("leave this frame out")
        self.left_out.setToolTip("Left out of every total; the table keeps it")
        self.info = QtWidgets.QLabel("")
        self.info.setObjectName("muted")
        for w in (self.prev, self.frame, self.next):
            row.addWidget(w)
        row.addStretch(1)
        col.addLayout(row)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.subtracted)
        row.addWidget(self.left_out)
        row.addStretch(1)
        col.addLayout(row)
        col.addWidget(self.info)

        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.view = pg.ImageView()
        self.view.ui.roiBtn.hide()
        self.view.ui.menuBtn.hide()
        self.view.setColorMap(phosphor_map())
        self.vb = self.view.getView()
        self.vb.invertY(True)
        self.vb.setAspectLocked(True)
        self.ions = pg.ScatterPlotItem(pxMode=False, brush=None,
                                       pen=pg.mkPen(ISOLATED, width=1.4))
        self.vb.addItem(self.ions)
        self.outer = self.inner = None
        split.addWidget(self.view)
        self.strip = scope_plot("frame", "ions")
        self.strip.setMinimumHeight(110)
        split.addWidget(self.strip)
        split.setSizes([520, 150])
        col.addWidget(split, 1)
        self.empty = empty_overlay(self.view, "Add a release video on the "
                                   "left, then Analyse.")

        self.prev.clicked.connect(lambda: self.frame.setValue(
            self.frame.value() - 1))
        self.next.clicked.connect(lambda: self.frame.setValue(
            self.frame.value() + 1))
        self.frame.valueChanged.connect(self._show_frame)
        self.subtracted.toggled.connect(self._show_frame)
        self.left_out.toggled.connect(self._toggle_out)
        self.strip.scene().sigMouseClicked.connect(self._strip_clicked)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty.setGeometry(self.view.rect())

    def refresh(self):
        ds = self.page.current()
        self.empty.setVisible(ds is None)
        if ds is None:
            self.view.clear()
            self.strip.clear()
            return
        if self._key != (ds.path, ds.frames):
            self._key = (ds.path, ds.frames)
            self.items = ds.items()
        self.frame.blockSignals(True)
        self.frame.setRange(0, max(len(self.items) - 1, 0))
        self.frame.blockSignals(False)
        self._draw_region()
        self._draw_strip()
        self._show_frame()

    def current_frame(self):
        if not self.items:
            return None
        return frame_number(self.items[min(self.frame.value(),
                                           len(self.items) - 1)])

    def _show_frame(self, *_):
        ds, r = self.page.current(), self.page.current_result()
        if ds is None or not self.items:
            return
        it = self.items[min(self.frame.value(), len(self.items) - 1)]
        f = frame_number(it)
        params = self.page.settings.params()
        ions = []
        if r is not None and self.subtracted.isChecked():
            diff, ions, _cm, _disc = frame_view(ds, params, it, r.background)
            img = diff
        else:
            img = read_frame(it, params.grey)
        if img is None:
            return
        self.view.setImage(img, autoLevels=True)
        self.ions.setData([x + 0.5 for x, *_ in ions],
                          [y + 0.5 for _x, y, *_ in ions], size=12)
        self.left_out.blockSignals(True)
        self.left_out.setChecked(f in ds.exclude)
        self.left_out.blockSignals(False)
        text = f"{len(ions)} single ions" if r is not None else "not analysed"
        if r is not None:
            row = next((x for x in r.rows if x.frame == f), None)
            if row is not None:
                for name, m in row.methods.items():
                    text += f"  ·  {name}: {m.inner:g} in the disc"
        self.info.setText(text + ("  ·  left out" if f in ds.exclude else ""))

    def _toggle_out(self, on):
        f = self.current_frame()
        if f is not None:
            self.page.set_left_out(f, on)

    def _draw_strip(self):
        p = self.strip.getPlotItem()
        p.clear()
        r = self.page.current_result()
        if r is None:
            return
        name = r.method_names()[0]
        xs = [row.frame for row in r.rows]
        ys = [row.methods[name].total if name in row.methods else row.singles
              for row in r.rows]
        brushes = [qcolor(MUTED, 120) if row.excluded else qcolor(PHOSPHOR, 200)
                   for row in r.rows]
        p.addItem(pg.BarGraphItem(x=xs, height=ys, width=0.8, brushes=brushes,
                                  pen=None))

    def _strip_clicked(self, ev):
        vb = self.strip.getPlotItem().vb
        x = vb.mapSceneToView(ev.scenePos()).x()
        numbers = [frame_number(it) for it in self.items]
        if numbers:
            k = int(np.argmin([abs(n - x) for n in numbers]))
            self.frame.setValue(k)

    def _draw_region(self):
        for roi in (self.outer, self.inner):
            if roi is not None:
                self.vb.removeItem(roi)
        self.outer = self.inner = None
        reg = self.page.settings.params().region
        pen = pg.mkPen(AMBER, width=1.5)
        if reg.kind in ("circle", "ring"):
            self.outer = pg.CircleROI((reg.cx - reg.r, reg.cy - reg.r),
                                      (2 * reg.r, 2 * reg.r), pen=pen)
        elif reg.kind == "rect":
            self.outer = pg.RectROI((reg.x0, reg.y0),
                                    (reg.x1 - reg.x0, reg.y1 - reg.y0), pen=pen)
        if reg.kind == "ring":
            self.inner = pg.CircleROI(
                (reg.inner_cx - reg.inner_r, reg.inner_cy - reg.inner_r),
                (2 * reg.inner_r, 2 * reg.inner_r),
                pen=pg.mkPen(PHOSPHOR, width=1.5))
        for roi in (self.outer, self.inner):
            if roi is not None:
                self.vb.addItem(roi)
                roi.sigRegionChangeFinished.connect(self._region_dragged)

    def _region_dragged(self, *_):
        reg = self.page.settings.params().region
        kw = {}
        if self.outer is not None:
            (x, y), (w, h) = self.outer.pos(), self.outer.size()
            if reg.kind == "rect":
                kw.update(x0=int(round(x)), y0=int(round(y)),
                          x1=int(round(x + w)), y1=int(round(y + h)))
            else:
                kw.update(cx=round(x + w / 2, 1), cy=round(y + h / 2, 1),
                          r=round(w / 2, 1))
        if self.inner is not None:
            (x, y), (w, h) = self.inner.pos(), self.inner.size()
            kw.update(inner_cx=round(x + w / 2, 1), inner_cy=round(y + h / 2, 1),
                      inner_r=round(w / 2, 1))
        self.page.settings.set_region(dataclasses.replace(reg, **kw))


class CalibrationView(QtWidgets.QWidget):
    title = "calibration"

    def __init__(self, page):
        super().__init__()
        self.page = page
        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(0, 6, 0, 0)
        row = QtWidgets.QHBoxLayout()
        self.method = combo()
        row.addWidget(labelled(self.method, "method"))
        self.summary = QtWidgets.QLabel("")
        row.addWidget(self.summary, 1)
        col.addLayout(row)
        self.plot = scope_plot("light of one single ion", "ions")
        col.addWidget(self.plot, 2)
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["frame", "ions used", "SIS"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)
        col.addWidget(self.table, 1)
        self.method.currentTextChanged.connect(lambda _: self.refresh())

    def refresh(self):
        r = self.page.current_result()
        names = [m for m in _method_names(r) if r and m in r.light]
        if [self.method.itemText(k) for k in range(self.method.count())] != names:
            self.method.blockSignals(True)
            self.method.clear()
            self.method.addItems(names)
            self.method.blockSignals(False)
        p = self.plot.getPlotItem()
        p.clear()
        self.table.setRowCount(0)
        name = self.method.currentText()
        if r is None or name not in r.light:
            self.summary.setText("no pile-up method: nothing to calibrate"
                                 if r is not None else "")
            return
        light = np.concatenate([v for f, v in r.light[name].items()
                                if not next(x for x in r.rows
                                            if x.frame == f).excluded]
                               or [np.zeros(0)])
        if light.size:
            counts, edges = np.histogram(light, bins=min(60, max(10, light.size // 5)))
            p.addItem(pg.PlotDataItem(edges, counts, stepMode="center",
                                      fillLevel=0, brush=qcolor(PHOSPHOR, 60),
                                      pen=pg.mkPen(PHOSPHOR, width=1.2)))
        info = r.methods[name]
        sis_values = [row.methods[name].sis for row in r.rows
                      if row.methods[name].sis is not None and not row.excluded]
        if info.sis is not None:
            line, text = info.sis, f"one SIS for all frames: {info.sis:.4g}"
        elif sis_values:
            line = float(np.median(sis_values))
            text = f"SIS per frame, median {line:.4g}"
        else:
            line, text = None, "no SIS"
        if line is not None:
            p.addItem(pg.InfiniteLine(line, angle=90,
                                      pen=pg.mkPen(AMBER, width=1.6)))
        bg = info.background_per_pixel
        self.summary.setText(text + (f"  ·  background {bg:.4g} per pixel"
                                     if bg else ""))
        self.table.setRowCount(len(r.rows))
        for i, row in enumerate(r.rows):
            m = row.methods[name]
            vals = [str(row.frame) + (" (left out)" if row.excluded else ""),
                    str(m.sis_ions), "" if m.sis is None else f"{m.sis:.4g}"]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QtWidgets.QTableWidgetItem(v))


class PileupView(QtWidgets.QWidget):
    title = "pile-up"

    def __init__(self, page):
        super().__init__()
        self.page = page
        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(0, 6, 0, 0)
        self.summary = QtWidgets.QLabel("")
        col.addWidget(self.summary)
        self.plot = scope_plot("frame", "ions in the pile-up disc")
        self.plot.getPlotItem().addLegend(offset=(-10, 10))
        col.addWidget(self.plot, 2)
        self.table = QtWidgets.QTableWidget(0, 0)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        col.addWidget(self.table, 1)

    def refresh(self):
        r = self.page.current_result()
        p = self.plot.getPlotItem()
        p.clear()
        self.table.setRowCount(0)
        if r is None:
            self.summary.setText("")
            return
        names = [n for n in r.method_names() if n in r.methods]
        parts = []
        for k, name in enumerate(names):
            c = SERIES[k % len(SERIES)]
            p.addItem(pg.PlotDataItem(
                [row.frame for row in r.rows],
                [row.methods[name].inner for row in r.rows],
                pen=pg.mkPen(c, width=1.6), symbol="o", symbolSize=6,
                symbolBrush=c, symbolPen=None, name=name))
        for name, t in r.totals.items():
            parts.append(f"{name}: {t.count:g} = {t.singles} single "
                         f"+ {t.inner:g} in the disc ({t.frames} frames)")
        self.summary.setText("   ·   ".join(parts) or "")
        heads = ["frame", "single ions"]
        for name in names:
            heads += [f"{name}: S", f"{name}: disc", f"{name}: total"]
        self.table.setColumnCount(len(heads))
        self.table.setHorizontalHeaderLabels(heads)
        self.table.setRowCount(len(r.rows))
        for i, row in enumerate(r.rows):
            vals = [f"{row.frame}" + (" (left out)" if row.excluded else ""),
                    str(row.singles)]
            for name in names:
                m = row.methods[name]
                vals += [f"{m.signal:.4g}", f"{m.inner:g}",
                         f"{m.total:g}" + (" (skipped)" if m.skipped else "")]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QtWidgets.QTableWidgetItem(v))


class ErrorsView(QtWidgets.QWidget):
    title = "errors"
    COLUMNS = ["name", "kind", "group", "fraction", "value", "methods",
               "spread", "per frame", "size"]

    def __init__(self, page):
        super().__init__()
        self.page = page
        self._busy = False
        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(0, 6, 0, 0)
        row = QtWidgets.QHBoxLayout()
        self.method = combo()
        self.combine = combo(COMBINE)
        row.addWidget(labelled(self.method, "count of"))
        row.addWidget(labelled(self.combine, "combine"))
        self.add = QtWidgets.QPushButton("Add component")
        self.remove = QtWidgets.QPushButton("Remove")
        row.addWidget(self.add)
        row.addWidget(self.remove)
        row.addStretch(1)
        col.addLayout(row)
        self.table = QtWidgets.QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)
        col.addWidget(self.table, 1)
        self.result = QtWidgets.QLabel("")
        self.result.setWordWrap(True)
        col.addWidget(self.result)
        note = QtWidgets.QLabel(
            "Nothing is added by default. poisson: sqrt(N); method_spread: "
            "std or half range of the methods' totals; fraction: fraction x "
            "N; absolute: the value; per_frame: frame errors in quadrature.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        col.addWidget(note)
        self.add.clicked.connect(self._add)
        self.remove.clicked.connect(self._remove)
        self.method.currentTextChanged.connect(lambda _: self._store())
        self.combine.currentTextChanged.connect(lambda _: self._store())
        self.table.itemChanged.connect(lambda _: self._store())

    def _combo(self, values, current):
        c = QtWidgets.QComboBox()
        c.addItems(values)
        c.setCurrentText(current)
        c.currentTextChanged.connect(lambda _: self._store())
        return c

    def refresh(self):
        ds, r = self.page.current(), self.page.current_result()
        self._busy = True
        names = [""] + _method_names(r)
        self.method.clear()
        self.method.addItems(names)
        self.table.setRowCount(0)
        if ds is not None:
            t = ds.errors
            self.method.setCurrentText(t.method)
            self.combine.setCurrentText(t.combine)
            for c in t.components:
                self._add_row(c)
        self._busy = False
        self._show()

    def _add_row(self, c):
        i = self.table.rowCount()
        self.table.insertRow(i)
        self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(c.name))
        self.table.setCellWidget(i, 1, self._combo(KINDS, c.kind))
        self.table.setCellWidget(i, 2, self._combo(GROUPS, c.group))
        self.table.setItem(i, 3, QtWidgets.QTableWidgetItem(f"{c.fraction:g}"))
        self.table.setItem(i, 4, QtWidgets.QTableWidgetItem(f"{c.value:g}"))
        self.table.setItem(i, 5, QtWidgets.QTableWidgetItem(", ".join(c.methods)))
        self.table.setCellWidget(i, 6, self._combo(SPREADS, c.spread))
        self.table.setCellWidget(i, 7, self._combo(PER_FRAME, c.per_frame))
        size = QtWidgets.QTableWidgetItem("")
        size.setFlags(size.flags() & ~QtCore.Qt.ItemIsEditable)
        self.table.setItem(i, 8, size)

    def table_value(self):
        comps = []
        for i in range(self.table.rowCount()):
            def text(j):
                it = self.table.item(i, j)
                return it.text().strip() if it else ""
            def num(j):
                try:
                    return float(text(j) or 0)
                except ValueError:
                    return 0.0
            comps.append(ErrorComponent(
                text(0) or f"component {i + 1}",
                self.table.cellWidget(i, 1).currentText(),
                self.table.cellWidget(i, 2).currentText(),
                num(3), num(4),
                tuple(m.strip() for m in text(5).split(",") if m.strip()),
                self.table.cellWidget(i, 6).currentText(),
                self.table.cellWidget(i, 7).currentText()))
        return ErrorTable(tuple(comps), self.method.currentText(),
                          self.combine.currentText())

    def _store(self):
        if self._busy:
            return
        ds = self.page.current()
        if ds is None:
            return
        try:
            ds.errors = self.table_value().check()
        except ValueError as e:
            self.result.setText(str(e))
            return
        self._show()

    def _show(self):
        ds, r = self.page.current(), self.page.current_result()
        if ds is None or r is None:
            self.result.setText("Analyse the dataset to see the errors."
                                if ds is not None else "")
            return
        try:
            e = evaluate(ds.errors, r)
        except ValueError as err:
            self.result.setText(str(err))
            return
        self._busy = True
        for i, (_name, _g, v) in enumerate(e.components):
            if i < self.table.rowCount():
                self.table.item(i, 8).setText(f"{v:.4g}")
        self._busy = False
        self.result.setText(
            f"N = {e.count:g} ({e.method})   ·   statistical {e.statistical:.4g}"
            f"   ·   systematic {e.systematic:.4g}   ·   total {e.total:.4g}")

    def _add(self):
        ds = self.page.current()
        if ds is None:
            return
        n = self.table.rowCount() + 1
        self._busy = True
        self._add_row(ErrorComponent(f"component {n}"))
        self._busy = False
        self._store()

    def _remove(self):
        i = self.table.currentRow()
        if i >= 0:
            self.table.removeRow(i)
            self._store()


class DecayView(QtWidgets.QWidget):
    title = "decay"

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.fit = None
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 6, 0, 0)
        left = QtWidgets.QVBoxLayout()
        self.plot = scope_plot("storage time (s)", "ions")
        left.addWidget(self.plot, 1)
        self.result = QtWidgets.QLabel("")
        self.result.setWordWrap(True)
        left.addWidget(self.result)
        row.addLayout(left, 1)

        side = QtWidgets.QVBoxLayout()
        self.series = combo()
        side.addWidget(labelled(self.series, "series"))
        self.points = QtWidgets.QListWidget()
        self.points.setMinimumWidth(220)
        side.addWidget(self.points, 1)
        self.method = combo()
        side.addWidget(labelled(self.method, "count of"))
        self.fit_btn = QtWidgets.QPushButton("Fit N0 exp(-t / tau)")
        self.fit_btn.setObjectName("primary")
        side.addWidget(self.fit_btn)
        two = QtWidgets.QGroupBox("tau from two datasets")
        tl = QtWidgets.QVBoxLayout(two)
        self.first = combo()
        self.second = combo()
        self.propagation = combo(PROPAGATIONS)
        tl.addWidget(labelled(self.first, "first"))
        tl.addWidget(labelled(self.second, "second"))
        tl.addWidget(labelled(self.propagation, "error"))
        self.two_btn = QtWidgets.QPushButton("Two-point tau")
        tl.addWidget(self.two_btn)
        self.two_result = QtWidgets.QLabel("")
        self.two_result.setWordWrap(True)
        tl.addWidget(self.two_result)
        side.addWidget(two)
        row.addLayout(side)
        self.series.currentTextChanged.connect(lambda _: self._fill_points())
        self.fit_btn.clicked.connect(self.do_fit)
        self.two_btn.clicked.connect(self.do_two)

    def _ready(self):
        """Datasets with a result and a storage time."""
        return [ds for ds in self.page.datasets
                if ds.name in self.page.results and ds.storage_time is not None]

    def refresh(self):
        ready = self._ready()
        series = ["all"] + sorted({ds.series for ds in ready if ds.series})
        cur = self.series.currentText()
        self.series.blockSignals(True)
        self.series.clear()
        self.series.addItems(series)
        self.series.setCurrentText(cur if cur in series else "all")
        self.series.blockSignals(False)
        methods = []
        for ds in ready:
            for m in self.page.results[ds.name].method_names():
                if m not in methods:
                    methods.append(m)
        cur = self.method.currentText()
        self.method.clear()
        self.method.addItems([""] + methods)
        self.method.setCurrentText(cur)
        names = [ds.name for ds in ready]
        for c in (self.first, self.second):
            cur = c.currentText()
            c.clear()
            c.addItems(names)
            c.setCurrentText(cur)
        if self.second.currentIndex() == 0 and len(names) > 1:
            self.second.setCurrentIndex(1)
        self._fill_points()

    def _fill_points(self):
        chosen = {self.points.item(k).text(): self.points.item(k).checkState()
                  for k in range(self.points.count())}
        self.points.clear()
        s = self.series.currentText()
        for ds in self._ready():
            if s not in ("", "all") and ds.series != s:
                continue
            it = QtWidgets.QListWidgetItem(ds.name)
            it.setFlags(it.flags() | QtCore.Qt.ItemIsUserCheckable)
            it.setCheckState(chosen.get(ds.name, QtCore.Qt.Checked))
            self.points.addItem(it)

    def point(self, ds):
        """(t, N, error) of a dataset: its count and its error table's total,
        for the chosen method (or the table's own)."""
        r = self.page.results[ds.name]
        table = ds.errors
        if self.method.currentText():
            table = dataclasses.replace(table, method=self.method.currentText())
        e = evaluate(table, r)
        return ds.storage_time, e.count, e.total

    def do_fit(self):
        names = [self.points.item(k).text() for k in range(self.points.count())
                 if self.points.item(k).checkState() == QtCore.Qt.Checked]
        by_name = {ds.name: ds for ds in self._ready()}
        try:
            pts = [self.point(by_name[n]) for n in names]
            self.fit = fit_decay(*zip(*pts)) if pts else None
        except ValueError as e:
            self.fit = None
            self.result.setText(str(e))
            self._draw([])
            return
        if self.fit is None:
            return
        f = self.fit
        self.result.setText(
            f"tau = {f.tau:.5g} ± {f.tau_err:.3g} s   ·   N0 = {f.n0:.5g} ± "
            f"{f.n0_err:.3g}   ·   cov(N0, tau) = {f.covariance[0][1]:.3g}   ·   "
            f"reduced chi² = {f.reduced_chi2:.3g} ({f.dof} dof), "
            f"{len(f.points)} datasets")
        self.page.fits = [("decay fit", f)]
        self._draw(f.points)

    def _draw(self, pts):
        p = self.plot.getPlotItem()
        p.clear()
        if not pts:
            return
        t, n, e = (np.array(v, float) for v in zip(*pts))
        p.addItem(pg.ErrorBarItem(x=t, y=n, top=e, bottom=e,
                                  pen=pg.mkPen(TEXT, width=1)))
        p.addItem(pg.ScatterPlotItem(t, n, size=8, brush=PHOSPHOR, pen=None))
        if self.fit is not None:
            ts = np.linspace(0, t.max() * 1.15, 200)
            p.addItem(pg.PlotDataItem(ts, self.fit.curve(ts),
                                      pen=pg.mkPen(AMBER, width=1.8)))

    def do_two(self):
        by_name = {ds.name: ds for ds in self._ready()}
        a, b = self.first.currentText(), self.second.currentText()
        if a not in by_name or b not in by_name or a == b:
            self.two_result.setText("Choose two different datasets.")
            return
        try:
            (t1, n1, e1), (t2, n2, e2) = self.point(by_name[a]), self.point(by_name[b])
            tau, err = two_point_tau(t1, n1, e1, t2, n2, e2,
                                     self.propagation.currentText())
        except ValueError as e:
            self.two_result.setText(str(e))
            return
        self.two_result.setText(f"tau = {tau:.5g} ± {err:.3g} s")


class ExportView(QtWidgets.QWidget):
    title = "export"

    def __init__(self, page):
        super().__init__()
        self.page = page
        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(10, 12, 10, 10)
        row = QtWidgets.QHBoxLayout()
        self.folder = QtWidgets.QLineEdit(
            QtCore.QSettings().value("ion_export_dir", ""))
        self.folder.setPlaceholderText("folder for the report")
        browse = QtWidgets.QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.folder, 1)
        row.addWidget(browse)
        col.addLayout(row)
        note = QtWidgets.QLabel(
            "frames_<dataset>.csv: every frame, left-out frames marked; "
            "totals.csv: the count of every dataset and method with its "
            "errors; errors.csv: every error component; report.json: all of "
            "it with the settings and the decay fit.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        col.addWidget(note)
        self.go = QtWidgets.QPushButton("Export")
        self.go.setObjectName("primary")
        self.go.clicked.connect(self.export)
        col.addWidget(self.go, 0, QtCore.Qt.AlignLeft)
        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        col.addWidget(self.status)
        col.addStretch(1)

    def refresh(self):
        self.go.setEnabled(bool(self.page.results))

    def _browse(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Report folder",
                                                       self.folder.text())
        if d:
            self.folder.setText(d)

    def export(self):
        folder = self.folder.text().strip()
        if not folder:
            self.status.setText("Choose a folder first.")
            return
        results = [self.page.results[ds.name] for ds in self.page.datasets
                   if ds.name in self.page.results]
        try:
            files = report.write(folder, results, self.page.fits)
        except (OSError, ValueError) as e:
            self.status.setText(f"export failed: {e}")
            return
        QtCore.QSettings().setValue("ion_export_dir", folder)
        self.status.setText(f"wrote {len(files)} files to {folder}")
        self.page.s.log(f"ions: report written to {folder}", "ok")


VIEWS = (ReleaseView, CalibrationView, PileupView, ErrorsView, DecayView,
         ExportView)
