"""ions: release videos of ions. Single ions are counted one by one, a pile-up
disc where they overlap is estimated from its light, the single-ion signal
calibrates it; errors, the decay with storage time and an export follow.
The analysis is ion_analysis; this page only shows it and holds the
datasets, the settings and the results."""

import os

from PySide6 import QtCore, QtWidgets

from ...ion_analysis import (IonDataset, find_datasets, format_frames, load,
                             parse_frames, recount, save)
from ...single_image_analysis import READ_EXTS, VIDEO_EXTS
from ..workers import IonWorker
from .base import Page
from .ions_settings import SettingsPanel
from .ions_views import VIEWS

COLUMNS = ["dataset", "time (s)", "series", "frames", "left out"]


class IonsPage(Page):
    title = "ions"
    hint = ("Ion release videos: single ions, pile-up disc, calibration, "
            "errors, decay with storage time")

    def __init__(self, session):
        super().__init__(session)
        self.datasets = []                 # ion_analysis.IonDataset
        self.results = {}                  # dataset name -> IonResult
        self.fits = []                     # (label, DecayFit) for the export
        self.stale = set()                 # results made with other settings
        self._thread = self._worker = None

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(8, 8, 0, 8)
        # three parts side by side that share the width (nothing fixed, so
        # this page never makes the window wider than the other pages do)
        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        row.addWidget(split)

        # datasets
        left = QtWidgets.QVBoxLayout()
        buttons = QtWidgets.QGridLayout()
        self.add_video = QtWidgets.QPushButton("Add videos…")
        self.add_video.setToolTip("Release videos or image files: one "
                                  "dataset each")
        self.add_folder = QtWidgets.QPushButton("Add folder…")
        self.add_folder.setToolTip("Every video and folder of frames under a "
                                   "folder, storage times from the names")
        self.background = QtWidgets.QPushButton("Background video…")
        self.background.setToolTip("A separate video the background is made "
                                   "of (settings: background made from video)")
        self.remove = QtWidgets.QPushButton("Remove")
        buttons.addWidget(self.add_video, 0, 0)
        buttons.addWidget(self.add_folder, 0, 1)
        buttons.addWidget(self.background, 1, 0)
        buttons.addWidget(self.remove, 1, 1)
        left.addLayout(buttons)
        self.table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        h.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.setToolTip("time: storage time in s. frames: first-last "
                              "used (empty: all). left out: frames left out "
                              "of the totals, e.g. 0-1, 5")
        left.addWidget(self.table, 1)
        run = QtWidgets.QHBoxLayout()
        self.analyse_btn = QtWidgets.QPushButton("Analyse")
        self.analyse_btn.setObjectName("primary")
        self.analyse_btn.setToolTip("Analyse the selected dataset")
        self.analyse_all_btn = QtWidgets.QPushButton("Analyse all")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        for b in (self.analyse_btn, self.analyse_all_btn, self.cancel_btn):
            run.addWidget(b)
        left.addLayout(run)
        self.progress = QtWidgets.QProgressBar()
        self.progress.hide()
        left.addWidget(self.progress)
        self.status = QtWidgets.QLabel("Add a release video to begin.")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        left.addWidget(self.status)
        holder = QtWidgets.QWidget()
        holder.setLayout(left)
        holder.setMinimumWidth(200)
        split.addWidget(holder)

        # views
        self.tabs = QtWidgets.QTabWidget()
        self.views = [cls(self) for cls in VIEWS]
        for v in self.views:
            self.tabs.addTab(v, v.title)
        split.addWidget(self.tabs)
        self.empty = self.views[0].empty          # "add a video" when empty

        # settings
        self.settings = SettingsPanel()
        self.settings.setMinimumWidth(220)
        split.addWidget(self.settings)
        split.setStretchFactor(1, 1)
        split.setCollapsible(1, False)
        split.setSizes([300, 900, 310])

        self.add_video.clicked.connect(self.pick_videos)
        self.add_folder.clicked.connect(self.pick_folder)
        self.background.clicked.connect(self.pick_background)
        self.remove.clicked.connect(self.remove_current)
        self.table.itemSelectionChanged.connect(self._selected)
        self.table.itemChanged.connect(self._edited)
        self.analyse_btn.clicked.connect(lambda: self.analyse(
            [self.current()] if self.current() else []))
        self.analyse_all_btn.clicked.connect(
            lambda: self.analyse(self.datasets))
        self.cancel_btn.clicked.connect(self.cancel)
        self.tabs.currentChanged.connect(lambda _: self._refresh_view())
        self.settings.paramsChanged.connect(self._params_changed)

    # ── datasets ──────────────────────────────────────────────────────────
    def current(self):
        k = self.table.currentRow()
        return self.datasets[k] if 0 <= k < len(self.datasets) else None

    def current_result(self):
        ds = self.current()
        return self.results.get(ds.name) if ds else None

    def add_datasets(self, datasets):
        names = {d.name for d in self.datasets}
        for ds in datasets:
            base, k = ds.name, 2
            while ds.name in names:
                ds.name, k = f"{base}-{k}", k + 1
            names.add(ds.name)
            self.datasets.append(ds)
        self._fill_table()
        if self.datasets and self.table.currentRow() < 0:
            self.table.selectRow(0)
        self.s.log(f"ions: {len(datasets)} dataset(s) added")

    def pick_videos(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Add release videos", QtCore.QSettings().value("last_dir", ""),
            "Videos and images (" + " ".join("*" + e for e in READ_EXTS) + ")")
        if files:
            self.add_datasets([IonDataset(os.path.splitext(os.path.basename(f))[0],
                                          f) for f in files])

    def pick_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Add a folder of release videos",
            QtCore.QSettings().value("last_dir", ""))
        if d:
            found = find_datasets(d)
            if not found:
                self.s.log(f"ions: no videos or frames in {d}", "warn")
            self.add_datasets(found)

    def pick_background(self):
        ds = self.current()
        if ds is None:
            return
        f, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, f"Background video for {ds.name}", os.path.dirname(ds.path),
            "Videos (" + " ".join("*" + e for e in VIDEO_EXTS) + ")")
        if f:
            ds.background_source = f
            self._invalidate(ds)

    def remove_current(self):
        ds = self.current()
        if ds is None:
            return
        self.datasets.remove(ds)
        self.results.pop(ds.name, None)
        self._fill_table()
        self._refresh_view()

    def _fill_table(self):
        self.table.blockSignals(True)
        row = self.table.currentRow()
        self.table.setRowCount(len(self.datasets))
        for i, ds in enumerate(self.datasets):
            frames = "" if ds.frames is None else \
                f"{ds.frames[0]}-{ds.frames[1] - 1}"
            vals = [ds.name + ("  •" if ds.name in self.stale else ""),
                    "" if ds.storage_time is None else f"{ds.storage_time:g}",
                    ds.series, frames, format_frames(ds.exclude)]
            for j, v in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(v)
                if j == 0:
                    it.setFlags(it.flags() & ~QtCore.Qt.ItemIsEditable)
                    it.setToolTip(ds.path + ("\nanalysed with other settings"
                                             if ds.name in self.stale else ""))
                self.table.setItem(i, j, it)
        self.table.blockSignals(False)
        if 0 <= row < len(self.datasets):
            self.table.selectRow(row)

    def _edited(self, item):
        ds = self.datasets[item.row()]
        text = item.text().strip()
        col = COLUMNS[item.column()]
        try:
            if col == "time (s)":
                ds.storage_time = float(text) if text else None
            elif col == "series":
                ds.series = text
            elif col == "frames":
                if text:
                    a, b = (int(x) for x in text.split("-"))
                    ds.frames = (a, b + 1)
                else:
                    ds.frames = None
                self._invalidate(ds)
            elif col == "left out":
                self.set_exclude(ds, parse_frames(text))
        except ValueError:
            self.s.log(f"ions: cannot read {text!r} for {col}", "warn")
            self._fill_table()
        self._refresh_view()

    def set_exclude(self, ds, frames):
        """Frames left out of the totals: counted again at once, without
        reading the video."""
        ds.exclude = tuple(sorted(set(frames)))
        r = self.results.get(ds.name)
        if r is not None:
            self.results[ds.name] = recount(r, ds.exclude)
        self._fill_table()
        self._refresh_view()

    def set_left_out(self, frame, on):
        ds = self.current()
        if ds is None:
            return
        frames = set(ds.exclude)
        if on:
            frames.add(frame)
        else:
            frames.discard(frame)
        self.set_exclude(ds, frames)

    def _invalidate(self, ds):
        self.results.pop(ds.name, None)
        self.stale.discard(ds.name)
        self._fill_table()
        self._refresh_view()

    def _selected(self):
        self._refresh_view()

    def save_dataset(self, path, ds=None):
        save(path, ds or self.current(), self.settings.params())

    def load_dataset(self, path):
        ds, params = load(path)
        self.settings.set_params(params)
        self.add_datasets([ds])

    # ── analysis ──────────────────────────────────────────────────────────
    def _params_changed(self):
        self.stale |= set(self.results)
        self._fill_table()
        if self.isVisible():
            self.views[0].refresh()
        if self.results:
            self.status.setText("The settings changed since the last "
                                "analysis (•): Analyse again.")

    def analyse(self, datasets):
        datasets = [d for d in datasets if d is not None]
        if not datasets or self._thread is not None:
            return
        params = self.settings.params()
        self._thread = QtCore.QThread(self)
        self._worker = IonWorker(datasets, params)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        queued = QtCore.Qt.QueuedConnection
        self._worker.progress.connect(self._on_progress, queued)
        self._worker.one.connect(self._on_result, queued)
        self._worker.failed.connect(self._on_failed, queued)
        self._worker.finished.connect(self._on_finished, queued)
        self.progress.show()
        self._busy(True)
        self.s.log(f"ions: analysing {len(datasets)} dataset(s)")
        self._thread.start()

    def cancel(self):
        if self._worker is not None:
            self._worker.cancel()

    def _busy(self, on):
        for b in (self.analyse_btn, self.analyse_all_btn, self.add_video,
                  self.add_folder, self.remove):
            b.setEnabled(not on)
        self.cancel_btn.setEnabled(on)

    @QtCore.Slot(str, int, int)
    def _on_progress(self, name, done, total):
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.status.setText(f"{name}: frame {done} of {total}")

    @QtCore.Slot(object)
    def _on_result(self, r):
        self.results[r.dataset.name] = r
        self.stale.discard(r.dataset.name)
        parts = [f"{n} {t.count:g}" for n, t in r.totals.items()]
        self.s.log(f"ions: {r.dataset.name}: " + ", ".join(parts), "ok")
        self._fill_table()
        self._refresh_view()

    @QtCore.Slot(str, str)
    def _on_failed(self, name, msg):
        self.s.log(f"ions: {name}: {msg}", "error")

    @QtCore.Slot(bool)
    def _on_finished(self, cancelled):
        self._thread.quit()
        self._thread.wait()
        self._thread = self._worker = None
        self.progress.hide()
        self._busy(False)
        self.status.setText("Cancelled." if cancelled else
                            f"{len(self.results)} dataset(s) analysed.")

    # ── showing ───────────────────────────────────────────────────────────
    def _refresh_view(self):
        if self.isVisible():
            self.tabs.currentWidget().refresh()

    def refresh(self):
        self._refresh_view()

    def shown(self):
        super().shown()
        self._refresh_view()

    def showEvent(self, e):
        super().showEvent(e)
        self._refresh_view()

    def stop(self):
        """Cancel a running analysis and wait for it (the window closes)."""
        self.cancel()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(10000)

    @staticmethod
    def dataset_from_path(path):
        """One dataset for a video, image or folder of frames."""
        name = os.path.splitext(os.path.basename(os.path.normpath(path)))[0]
        return IonDataset(name, path)

