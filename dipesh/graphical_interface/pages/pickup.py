"""pickup: PicoScope traces for the current run, RF notch, pulse timing."""

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from ...pickup import (CHANNELS, PickupConfig, ScopeConfig, discover_scopes,
                       measure)
from ...single_image_analysis import parse_batman
from ..theme import (CHANNEL_COLOURS, MUTED, PHOSPHOR, RULE, TEXT,
                     plot_background, style_item)
from ..workers import _PickupJob, _PickupSignals
from .base import (Page, combo, empty_overlay, form, labelled, qcolor,
                   side_column)


class PickupPage(Page):
    title = "pickup"
    hint = "PicoScope traces for this run: RF notch, pulse time and size"

    def __init__(self, session):
        super().__init__(session)
        self.traces = []
        self.gen = 0
        # made in the GUI thread and kept by the page; jobs emit on it from
        # pool threads
        self.sig = _PickupSignals()
        self.sig.done.connect(self._done, QtCore.Qt.QueuedConnection)
        self.pool = QtCore.QThreadPool.globalInstance()
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._start)

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(8, 8, 0, 8)
        left = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        # one panel per scope: scope B sits thousands of µs later on the
        # shared clock, so a single axis squeezes both windows to slivers
        self.plot = pg.GraphicsLayoutWidget()
        self.plot.setBackground(plot_background())
        left.addWidget(self.plot)
        self.table = QtWidgets.QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["scope", "ch", "pulse", "time (µs)", "amplitude (mV)",
             "area (V·µs)", "FWHM (µs)", "S/N"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)
        left.addWidget(self.table)
        left.setSizes([560, 200])
        row.addWidget(left, 1)
        self.empty = empty_overlay(self.plot, "No PicoScope files in this "
                                   "run's folder.\nExpected names like "
                                   "Picoscope_chD_<tag>_….json")

        side, lay = side_column(310)
        v = form(lay, "view")
        self.mode = combo(["stacked", "one channel"])
        v.addRow(labelled(self.mode, "show"))
        self.chan = combo()
        v.addRow(labelled(self.chan, "channel"))
        self.show_raw = QtWidgets.QCheckBox("raw trace underneath")
        self.show_raw.setChecked(True)
        v.addRow(self.show_raw)

        s = QtWidgets.QGroupBox("scopes")
        sl = QtWidgets.QVBoxLayout(s)
        self.scopes = QtWidgets.QTableWidget(0, 3)
        self.scopes.setHorizontalHeaderLabels(["", "filename tag",
                                               "delay key"])
        self.scopes.verticalHeader().hide()
        sh = self.scopes.horizontalHeader()
        sh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        sh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.scopes.setMaximumHeight(110)
        self.scopes.setToolTip("Scope B's times are shifted by the Batman "
                               "parameter in 'delay key' so both scopes share "
                               "one experiment clock")
        sl.addWidget(self.scopes)
        sb = QtWidgets.QHBoxLayout()
        find = QtWidgets.QPushButton("Find in files")
        find.setToolTip("Read the scope tags from this run's filenames")
        find.clicked.connect(self._discover)
        sb.addWidget(find)
        addr = QtWidgets.QPushButton("Add")
        addr.clicked.connect(lambda: self._add_scope_row("", "", ""))
        sb.addWidget(addr)
        rem = QtWidgets.QPushButton("Remove")
        rem.clicked.connect(lambda: self.scopes.removeRow(
            max(0, self.scopes.currentRow())) or self._cfg_changed())
        sb.addWidget(rem)
        sl.addLayout(sb)
        lay.addWidget(s)

        rf = form(lay, "RF notch")
        self.rf_on = QtWidgets.QCheckBox("remove trap RF")
        rf.addRow(self.rf_on)
        self.rf_freq = QtWidgets.QDoubleSpinBox()
        self.rf_freq.setRange(0.01, 500)
        self.rf_freq.setDecimals(3)
        self.rf_freq.setSuffix(" MHz")
        rf.addRow("frequency", self.rf_freq)
        self.rf_harm = QtWidgets.QSpinBox()
        self.rf_harm.setRange(1, 10)
        rf.addRow("harmonics", self.rf_harm)
        self.rf_q = QtWidgets.QDoubleSpinBox()
        self.rf_q.setRange(1, 500)
        self.rf_q.setDecimals(1)
        self.rf_q.setToolTip("Higher Q = narrower notch")
        rf.addRow("Q", self.rf_q)
        chrow = QtWidgets.QHBoxLayout()
        self.rf_ch = {}
        for c in CHANNELS:
            cb = QtWidgets.QCheckBox(c)
            self.rf_ch[c] = cb
            chrow.addWidget(cb)
        rf.addRow("on channels", chrow)
        self.nsig = QtWidgets.QDoubleSpinBox()
        self.nsig.setRange(1, 100)
        self.nsig.setDecimals(1)
        self.nsig.setToolTip("A pulse must stand this many noise σ above the "
                             "baseline to count as found")
        rf.addRow("pulse ≥ (σ)", self.nsig)

        self.apply_all = QtWidgets.QPushButton("Apply to all counted runs")
        self.apply_all.setToolTip("Re-measure the pickup of every counted run "
                                  "with these settings, for the plots page")
        self.apply_all.clicked.connect(self._apply_all)
        lay.addWidget(self.apply_all)
        self.rf_note = QtWidgets.QLabel("")
        self.rf_note.setObjectName("muted")
        self.rf_note.setWordWrap(True)
        lay.addWidget(self.rf_note)
        lay.addStretch(1)
        row.addWidget(side)

        self._load_cfg(session.pickup)
        self.mode.currentIndexChanged.connect(self._draw)
        self.chan.currentIndexChanged.connect(self._draw)
        self.show_raw.toggled.connect(self._draw)
        for w in (self.rf_freq, self.rf_q, self.nsig):
            w.valueChanged.connect(self._cfg_changed)
        self.rf_harm.valueChanged.connect(self._cfg_changed)
        self.rf_on.toggled.connect(self._cfg_changed)
        for cb in self.rf_ch.values():
            cb.toggled.connect(self._cfg_changed)
        self.scopes.itemChanged.connect(self._cfg_changed)
        session.currentChanged.connect(self.mark)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty.setGeometry(self.plot.rect())

    # config
    def _add_scope_row(self, label, tag, key):
        self.scopes.blockSignals(True)
        r = self.scopes.rowCount()
        self.scopes.insertRow(r)
        for c, v in enumerate((label or chr(ord("A") + r), tag, key or "")):
            it = QtWidgets.QTableWidgetItem(v)
            it.setToolTip(v)
            self.scopes.setItem(r, c, it)
        self.scopes.blockSignals(False)

    def _load_cfg(self, cfg):
        for w in (self.rf_freq, self.rf_harm, self.rf_q, self.nsig,
                  self.rf_on, *self.rf_ch.values()):
            w.blockSignals(True)
        self.scopes.setRowCount(0)
        for sc in cfg.scopes:
            self._add_scope_row(sc.label, sc.file_tag, sc.delay_key)
        self.rf_on.setChecked(cfg.rf_enabled)
        self.rf_freq.setValue(cfg.rf_freq_mhz)
        self.rf_harm.setValue(cfg.rf_harmonics)
        self.rf_q.setValue(cfg.rf_q)
        self.nsig.setValue(cfg.pulse_nsigma)
        for c, cb in self.rf_ch.items():
            cb.setChecked(c in cfg.rf_channels)
        for w in (self.rf_freq, self.rf_harm, self.rf_q, self.nsig,
                  self.rf_on, *self.rf_ch.values()):
            w.blockSignals(False)

    def _cfg(self):
        scopes = []
        for r in range(self.scopes.rowCount()):
            cell = lambda c: (self.scopes.item(r, c).text().strip()
                              if self.scopes.item(r, c) else "")
            if cell(1):
                scopes.append(ScopeConfig(cell(0) or chr(ord("A") + r),
                                          cell(1), cell(2) or None))
        return PickupConfig(
            scopes=scopes, rf_enabled=self.rf_on.isChecked(),
            rf_channels=tuple(c for c, cb in self.rf_ch.items()
                              if cb.isChecked()),
            rf_freq_mhz=self.rf_freq.value(),
            rf_harmonics=self.rf_harm.value(), rf_q=self.rf_q.value(),
            pulse_nsigma=self.nsig.value())

    def _cfg_changed(self, *_):
        self.s.pickup = self._cfg()
        self.mark()

    def _discover(self):
        if not self.s.current:
            return
        found = discover_scopes(self.s.current[1].folder)
        if not found:
            self.s.log("no PicoScope files in this run's folder", "warn")
            return
        old = {sc.label: sc.delay_key for sc in self.s.pickup.scopes}
        self.scopes.setRowCount(0)
        for sc in found:
            self._add_scope_row(sc.label, sc.file_tag, old.get(sc.label))
        self._cfg_changed()
        self.s.log(f"found {len(found)} scope(s): " +
                   ", ".join(f"{s.label} = {s.file_tag}" for s in found))

    # measuring
    def refresh(self):
        self.timer.start()

    def _start(self):
        cur = self.s.current
        if not cur:
            self.traces = []
            self._draw()
            return
        ds, it = cur
        r = ds.result(it) or self.s.live
        batman = r.batman if r is not None and r.item is it else {}
        if not batman:
            batman = parse_batman(it.folder)
        self.gen += 1
        self.pool.start(_PickupJob(self.gen, it.folder, batman,
                                   self.s.pickup, self.sig))

    @QtCore.Slot(int, object, object)
    def _done(self, gen, traces, err):
        if gen != self.gen:
            return
        if err:
            self.s.log(f"pickup: {err}", "error")
        self.traces = traces
        keys = [f"{t.scope}/ch{t.channel}" for t in traces]
        cur = self.chan.currentText()
        self.chan.blockSignals(True)
        self.chan.clear()
        self.chan.addItems(keys)
        pick = cur if cur in keys else next(
            (k for k in keys if k.endswith("chD")), keys[0] if keys else "")
        self.chan.setCurrentText(pick)
        self.chan.blockSignals(False)
        notes = {tuple(t.rf.get("notched_MHz", [])) for t in traces
                 if t.rf.get("applied")}
        skipped = [t.rf.get("reason") for t in traces if "reason" in t.rf]
        self.rf_note.setText(
            ("notched " + ", ".join(f"{f:.2f}" for f in
                                    sorted({x for n in notes for x in n}))
             + " MHz" if notes else "") +
            (f"\n{skipped[0]}" if skipped else ""))
        self._table()
        self._draw()

    def _table(self):
        t = self.traces
        self.table.setRowCount(len(t))
        for i, tr in enumerate(t):
            p = tr.pulse
            vals = [tr.scope, tr.channel, "found" if p["found"] else "none",
                    f"{p['peak_time_us']:.3f}" if p["found"] else "",
                    f"{p['amplitude_V'] * 1e3:.2f}" if p["found"] else "",
                    f"{p['area']:.4g}" if p["found"] else "",
                    f"{p['width_us']:.3f}" if p["found"] else "",
                    f"{p['n_sigma']:.1f}"]
            for j, v in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(v)
                it.setTextAlignment(QtCore.Qt.AlignCenter)
                if j == 1:
                    it.setForeground(QtGui.QBrush(QtGui.QColor(
                        CHANNEL_COLOURS.get(tr.channel, TEXT))))
                if j == 2:
                    it.setForeground(QtGui.QBrush(QtGui.QColor(
                        PHOSPHOR if p["found"] else MUTED)))
                self.table.setItem(i, j, it)

    def _panel(self, row, title, xlabel=True):
        pi = style_item(self.plot.addPlot(row=row, col=0))
        pi.setTitle(title, color=MUTED, justify="left", size="9pt")
        if xlabel:
            pi.setLabel("bottom", "experiment time (µs), scope A trigger = 0",
                        color=MUTED)
        return pi

    def _draw(self, *_):
        self.plot.clear()
        self.empty.setVisible(not self.traces)
        if not self.traces:
            return
        if self.mode.currentIndex() == 0:
            self._draw_stacked()
        else:
            self._draw_one()

    def _draw_stacked(self):
        """One panel per scope, each channel normalised to its own height and
        stacked, so a 5 mV pickup is as legible as a 1 V gate."""
        scopes = sorted({t.scope for t in self.traces})
        for k, sc in enumerate(scopes):
            tr_s = [t for t in self.traces if t.scope == sc]
            delay = tr_s[0].delay_us
            title = (f"scope {sc}" + (f", shifted by {delay:g} µs"
                                      if delay else ", reference"))
            p = self._panel(k, title, xlabel=(k == len(scopes) - 1))
            ticks, off = [], 0.0
            for tr in tr_s:
                v = tr.v
                span = float(np.ptp(v)) or 1.0
                y = (v - np.median(v)) / span
                col = CHANNEL_COLOURS.get(tr.channel, TEXT)
                p.plot(tr.t, y + off, pen=pg.mkPen(col, width=1))
                unit = (f"{span * 1e3:.3g} mV" if span < 1
                        else f"{span:.3g} V")
                ticks.append((off, f"ch{tr.channel}  {unit}"))
                if tr.pulse["found"]:
                    p.addItem(pg.InfiniteLine(
                        tr.pulse["peak_time_us"], angle=90,
                        pen=pg.mkPen(col, width=1, style=QtCore.Qt.DotLine)))
                off -= 1.35
            p.getAxis("left").setTicks([ticks])
            p.getAxis("left").setWidth(110)

    def _draw_one(self):
        key = self.chan.currentText()
        tr = next((t for t in self.traces
                   if f"{t.scope}/ch{t.channel}" == key), None)
        if tr is None:
            return
        col = CHANNEL_COLOURS.get(tr.channel, TEXT)
        rf = (f", RF notched at {', '.join(f'{f:.2f}' for f in tr.rf['notched_MHz'])} MHz"
              if tr.rf.get("applied") else "")
        p = self._panel(0, f"scope {tr.scope}, channel {tr.channel}{rf}")
        if self.show_raw.isChecked() and tr.rf.get("applied"):
            p.plot(tr.t, tr.v_raw * 1e3, pen=pg.mkPen(qcolor(MUTED, 120),
                                                      width=1))
        p.plot(tr.t, tr.v * 1e3, pen=pg.mkPen(col, width=1.4))
        pu = tr.pulse
        p.addItem(pg.InfiniteLine(pu["baseline"] * 1e3, angle=0,
                                  pen=pg.mkPen(RULE, width=1)))
        if pu["found"]:
            a, b = pu["region"]
            p.addItem(pg.LinearRegionItem((tr.t[a], tr.t[b]), movable=False,
                                          brush=qcolor(col, 40),
                                          pen=pg.mkPen(None)))
            p.addItem(pg.InfiniteLine(
                pu["peak_time_us"], angle=90,
                pen=pg.mkPen(PHOSPHOR, width=1.2, style=QtCore.Qt.DashLine),
                label=f"{pu['peak_time_us']:.3f} µs   "
                      f"{pu['amplitude_V'] * 1e3:.2f} mV",
                labelOpts={"color": PHOSPHOR, "position": 0.92}))
        p.setLabel("left", "mV", color=MUTED)

    def _apply_all(self):
        cfg = self.s.pickup
        n = 0
        for ds in self.s.datasets:
            for r in ds.done():
                try:
                    _, r.pickup = measure(r.item.folder, r.batman, cfg)
                    n += 1
                except Exception as e:            # noqa: BLE001
                    self.s.log(f"pickup {r.item.name}: {e}", "error")
        self.s.log(f"pickup re-measured for {n} runs", "ok")
        self.s.resultsChanged.emit()
