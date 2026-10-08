"""Widgets around the pages: the detection panel, the list of datasets, the
console and the export dialog."""

import os
import time

from PySide6 import QtCore, QtGui, QtWidgets

from ..single_image_analysis import DetectionParams, scan
from .theme import AMBER, MUTED, PHOSPHOR, RED, TEXT, glow, marker_icon


class ParamSlider(QtWidgets.QWidget):
    """Slider + number box kept in sync; floats carried at fixed decimals."""
    valueChanged = QtCore.Signal(float)

    def __init__(self, label, lo, hi, value, decimals=0, step=1.0, tip=""):
        super().__init__()
        self._scale = 10 ** decimals
        self._busy = False
        lab = QtWidgets.QLabel(label)
        lab.setMinimumWidth(118)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(int(lo * self._scale), int(hi * self._scale))
        self.slider.setValue(int(round(value * self._scale)))
        self.box = (QtWidgets.QDoubleSpinBox() if decimals
                    else QtWidgets.QSpinBox())
        if decimals:
            self.box.setDecimals(decimals)
        self.box.setRange(lo, hi)
        self.box.setSingleStep(step)
        self.box.setValue(value)
        self.box.setFixedWidth(74)
        self.box.setKeyboardTracking(False)
        self.box.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        if tip:
            self.setToolTip(tip)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 1, 0, 1)
        row.addWidget(lab)
        row.addWidget(self.slider, 1)
        row.addWidget(self.box)
        self.slider.valueChanged.connect(self._from_slider)
        self.box.valueChanged.connect(self._from_box)

    def _from_slider(self, v):
        if self._busy:
            return
        self._busy = True
        self.box.setValue(v / self._scale)
        self._busy = False
        self.valueChanged.emit(v / self._scale)

    def _from_box(self, v):
        if self._busy:
            return
        self._busy = True
        self.slider.setValue(int(round(v * self._scale)))
        self._busy = False
        self.valueChanged.emit(float(v))

    def value(self):
        return float(self.box.value())

    def setValue(self, v):
        self.box.setValue(v)


class DetectionPanel(QtWidgets.QWidget):
    """Detection settings and the live count. Shared by image and spots."""

    def __init__(self, session):
        super().__init__()
        self.s = session
        self.setFixedWidth(330)
        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(10, 10, 10, 10)
        col.setSpacing(6)

        self.count = QtWidgets.QLabel("–")
        self.count.setObjectName("count")
        self.count.setAlignment(QtCore.Qt.AlignCenter)
        glow(self.count)
        col.addWidget(self.count)
        self.count_sub = QtWidgets.QLabel("add a folder to start")
        self.count_sub.setObjectName("muted")
        self.count_sub.setAlignment(QtCore.Qt.AlignCenter)
        self.count_sub.setWordWrap(True)
        col.addWidget(self.count_sub)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(10)
        self.facts = {}
        for i, (k, label) in enumerate((("sigma", "noise σ"),
                                        ("thresh", "threshold used"),
                                        ("hot", "hot pixels fixed"),
                                        ("iso", "isolated spots"),
                                        ("lum", "count from light"))):
            a = QtWidgets.QLabel(label)
            a.setObjectName("muted")
            b = QtWidgets.QLabel("–")
            b.setAlignment(QtCore.Qt.AlignRight)
            grid.addWidget(a, i, 0)
            grid.addWidget(b, i, 1)
            self.facts[k] = b
        col.addLayout(grid)

        box = QtWidgets.QGroupBox("detection")
        bl = QtWidgets.QVBoxLayout(box)
        bl.setSpacing(2)
        d = DetectionParams()
        self.w = {
            "abs_thresh": ParamSlider("peak threshold", 0, 255, d.abs_thresh,
                0, 1, "A spot's background-subtracted peak must exceed this "
                "(0-255 scale). The main control."),
            "n_sigma": ParamSlider("noise multiple", 0, 40, d.n_sigma, 1, 0.5,
                "With adaptive on, the peak must also clear this many times "
                "the image noise — noisy frames get a stricter cut."),
            "sum_thresh": ParamSlider("5x5 sum min", 0, 600, d.sum_thresh,
                0, 5, "Minimum brightness summed over 5x5 pixels."),
            "spread_min": ParamSlider("spread min", 0, 25, d.spread_min, 1,
                0.5, "Minimum 5x5-sum / peak. A hot pixel has a low spread."),
            "min_dist": ParamSlider("min separation", 1, 60, d.min_dist, 0, 1,
                "Two peaks closer than this (px) count as one particle."),
            "hotpix_delta": ParamSlider("hot-pixel delta", 0, 200,
                d.hotpix_delta, 0, 5, "How far above its 3x3 median a pixel "
                "must be to count as hot. 0 turns the correction off."),
            "bg_blur_size": ParamSlider("background kernel", 3, 201,
                d.bg_blur_size, 0, 2, "Background estimation kernel (px). "
                "Larger follows uneven illumination more loosely."),
        }
        for wdg in self.w.values():
            bl.addWidget(wdg)
            wdg.valueChanged.connect(self._changed)
        self.adaptive = QtWidgets.QCheckBox("adaptive threshold")
        self.adaptive.setChecked(d.adaptive)
        self.adaptive.toggled.connect(self._changed)
        bl.addWidget(self.adaptive)
        col.addWidget(box)

        box2 = QtWidgets.QGroupBox("spot measurement")
        b2 = QtWidgets.QVBoxLayout(box2)
        b2.setSpacing(2)
        self.w2 = {
            "spot_max_radius": ParamSlider("max aperture", 3, 30,
                d.spot_max_radius, 0, 1, "Largest aperture a spot can grow "
                "to while its light is still increasing (px)."),
            "isolation_factor": ParamSlider("isolation factor", 0.5, 6,
                d.isolation_factor, 1, 0.1, "A spot is isolated when its "
                "nearest neighbour is further than this x its aperture."),
        }
        for wdg in self.w2.values():
            b2.addWidget(wdg)
            wdg.valueChanged.connect(self._changed)
        col.addWidget(box2)

        col.addStretch(1)
        row = QtWidgets.QHBoxLayout()
        reset = QtWidgets.QPushButton("Reset defaults")
        reset.clicked.connect(self.reset)
        row.addWidget(reset)
        save = QtWidgets.QPushButton("Save…")
        save.setToolTip("Save these settings to a .json file")
        save.clicked.connect(self._save)
        load = QtWidgets.QPushButton("Load…")
        load.setToolTip("Load settings from a .json, including a params.json "
                        "written by an export")
        load.clicked.connect(self._load)
        row.addWidget(save)
        row.addWidget(load)
        col.addLayout(row)

        session.liveChanged.connect(self._show_live)
        session.currentChanged.connect(self._show_live)

    def params(self):
        blur = int(self.w["bg_blur_size"].value())
        return self.s.params.replace(
            abs_thresh=self.w["abs_thresh"].value(),
            n_sigma=self.w["n_sigma"].value(),
            adaptive=self.adaptive.isChecked(),
            sum_thresh=self.w["sum_thresh"].value(),
            spread_min=self.w["spread_min"].value(),
            min_dist=int(self.w["min_dist"].value()),
            hotpix_delta=self.w["hotpix_delta"].value(),
            bg_blur_size=blur if blur % 2 else blur + 1,
            spot_max_radius=int(self.w2["spot_max_radius"].value()),
            isolation_factor=self.w2["isolation_factor"].value(),
        )

    def set_params(self, p):
        for k, wdg in {**self.w, **self.w2}.items():
            wdg.blockSignals(True)
            wdg.setValue(getattr(p, k))
            wdg.blockSignals(False)
        self.adaptive.blockSignals(True)
        self.adaptive.setChecked(p.adaptive)
        self.adaptive.blockSignals(False)
        self.s.set_params(p)

    def _changed(self, *_):
        self.s.set_params(self.params())

    def reset(self):
        self.set_params(DetectionParams(mcp_region=self.s.params.mcp_region))

    def _save(self):
        import json
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save settings", "detection_settings.json", "JSON (*.json)")
        if path:
            with open(path, "w") as f:
                json.dump({"params": self.s.params.to_dict()}, f, indent=2)
            self.s.log(f"settings saved to {path}")

    def _load(self):
        import json
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load settings", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path) as f:
                d = json.load(f)
            self.set_params(DetectionParams.from_dict(d.get("params", d)))
            self.s.log(f"settings loaded from {path}")
        except Exception as e:                    # noqa: BLE001
            self.s.log(f"could not load {path}: {e}", "error")

    def _show_live(self):
        r = self.s.live
        if not self.s.current:
            self.count.setText("–")
            self.count_sub.setText("add a folder to start")
            for b in self.facts.values():
                b.setText("–")
            return
        if r is None or r.item is not self.s.current[1]:
            self.count_sub.setText("detecting…")
            return
        if not r.ok:
            self.count.setText("!")
            self.count_sub.setText(r.error)
            return
        self.count.setText(str(r.n))
        self.count_sub.setText(f"antiprotons in run {r.item.name}")
        i = r.info
        self.facts["sigma"].setText(f"{i.sigma:.2f}")
        self.facts["thresh"].setText(f"{i.thresh:.0f}")
        self.facts["hot"].setText(str(i.hot_pixels))
        self.facts["iso"].setText(str(sum(s.is_isolated for s in r.spots)))
        self.facts["lum"].setText(f"{i.pbar_count_lum:.1f}")


class Sidebar(QtWidgets.QWidget):
    """Datasets and their runs. Drop folders or images here to add them."""

    def __init__(self, session):
        super().__init__()
        self.s = session
        self.setMinimumWidth(250)
        self.setAcceptDrops(True)
        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(8, 10, 4, 8)
        col.setSpacing(6)

        row = QtWidgets.QHBoxLayout()
        self.add_folder = QtWidgets.QPushButton("Add folder…")
        self.add_folder.setToolTip("A folder of pbar_run_XXXXXX folders, one "
                                   "run folder, or a folder of images (Ctrl+O)")
        self.add_images = QtWidgets.QPushButton("Add images…")
        self.add_images.setToolTip("Pick image files directly (Ctrl+Shift+O)")
        row.addWidget(self.add_folder)
        row.addWidget(self.add_images)
        col.addLayout(row)

        self.filter = QtWidgets.QLineEdit()
        self.filter.setPlaceholderText("filter runs")
        self.filter.setClearButtonEnabled(True)
        col.addWidget(self.filter)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["run", "p̄"])
        self.tree.setColumnCount(2)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        h = self.tree.header()
        h.setStretchLastSection(False)
        h.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        h.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        col.addWidget(self.tree, 1)

        self.empty = QtWidgets.QLabel(
            "Add a folder of runs, or drop one here.\n\nEach folder you add "
            "becomes a dataset — add pbar, background and ion runs "
            "separately to compare them.")
        self.empty.setObjectName("empty")
        self.empty.setWordWrap(True)
        self.empty.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        col.addWidget(self.empty)

        self.summary = QtWidgets.QLabel("")
        self.summary.setObjectName("muted")
        col.addWidget(self.summary)

        self.add_folder.clicked.connect(self.pick_folder)
        self.add_images.clicked.connect(self.pick_images)
        self.filter.textChanged.connect(self._apply_filter)
        self.tree.currentItemChanged.connect(self._picked)
        self.tree.itemChanged.connect(self._renamed)
        self.tree.customContextMenuRequested.connect(self._menu)
        session.datasetsChanged.connect(self.rebuild)
        session.resultsChanged.connect(self.update_counts)
        session.paramsChanged.connect(self.update_counts)
        self.rebuild()

    # adding
    def pick_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Add a folder of runs or images",
            QtCore.QSettings().value("last_dir", ""))
        if d:
            QtCore.QSettings().setValue("last_dir", os.path.dirname(d))
            self.add_paths([d])

    def pick_images(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Add images", QtCore.QSettings().value("last_dir", ""),
            "Images (*.tif *.tiff *.png)")
        if files:
            QtCore.QSettings().setValue("last_dir", os.path.dirname(files[0]))
            items = [it for f in files for it in scan(f)]
            name = os.path.basename(os.path.dirname(files[0])) or "images"
            self._add(name, items)

    def add_paths(self, paths):
        files = [p for p in paths if os.path.isfile(p)]
        for p in paths:
            if os.path.isdir(p):
                self._add(os.path.basename(os.path.normpath(p)), scan(p))
        if files:
            items = [it for f in files for it in scan(f)]
            self._add(os.path.basename(os.path.dirname(files[0])), items)

    def _add(self, name, items):
        if not items:
            self.s.log(f"nothing to analyse in {name}: no pbar_run_ folders, "
                       "TIFFs or images found", "warn")
            return
        ds = self.s.add(name, items)
        self.s.log(f"added dataset {ds.name}: {len(items)} images")
        if self.s.current is None:
            self.select(ds, items[0])

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.add_paths([u.toLocalFile() for u in e.mimeData().urls()])

    # tree
    def rebuild(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        self._nodes = {}
        for ds in self.s.datasets:
            top = QtWidgets.QTreeWidgetItem([ds.name, ""])
            top.setIcon(0, marker_icon(ds.colour, ds.symbol))
            top.setFlags(top.flags() | QtCore.Qt.ItemIsEditable)
            top.setData(0, QtCore.Qt.UserRole, ("ds", ds))
            top.setForeground(0, QtGui.QBrush(QtGui.QColor(ds.colour)))
            f = top.font(0); f.setBold(True); top.setFont(0, f)
            self.tree.addTopLevelItem(top)
            for it in ds.items:
                node = QtWidgets.QTreeWidgetItem([it.name, ""])
                node.setData(0, QtCore.Qt.UserRole, ("item", ds, it))
                node.setToolTip(0, it.path)
                node.setTextAlignment(1, QtCore.Qt.AlignRight)
                top.addChild(node)
                self._nodes[it.path] = node
            top.setExpanded(True)
        self.tree.blockSignals(False)
        self.empty.setVisible(not self.s.datasets)
        self.tree.setVisible(bool(self.s.datasets))
        self._apply_filter(self.filter.text())
        self.update_counts()
        if self.s.current:
            node = self._nodes.get(self.s.current[1].path)
            if node:
                self.tree.blockSignals(True)
                self.tree.setCurrentItem(node)
                self.tree.blockSignals(False)

    def update_counts(self):
        stale = self.s.stale
        for k in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(k)
            ds = top.data(0, QtCore.Qt.UserRole)[1]
            tot = 0
            for j in range(top.childCount()):
                node = top.child(j)
                it = node.data(0, QtCore.Qt.UserRole)[2]
                r = ds.result(it)
                if r is None:
                    node.setText(1, "")
                elif not r.ok:
                    node.setText(1, "err")
                    node.setForeground(1, QtGui.QBrush(QtGui.QColor(RED)))
                    node.setToolTip(1, r.error)
                else:
                    tot += r.n
                    node.setText(1, str(r.n))
                    node.setForeground(1, QtGui.QBrush(
                        QtGui.QColor(MUTED if stale else TEXT)))
                    node.setToolTip(1, "settings changed since this was "
                                       "counted — run all again" if stale
                                    else "")
            top.setText(1, str(tot) if ds.results else "")
        n = sum(len(d.items) for d in self.s.datasets)
        done = sum(len(d.done()) for d in self.s.datasets)
        self.summary.setText(f"{n} images, {done} counted" if n else "")

    def select(self, ds, item):
        node = self._nodes.get(item.path)
        if node:
            self.tree.setCurrentItem(node)

    def step(self, delta):
        """Move to the previous/next image, across datasets."""
        flat = self.s.all_items()
        if not flat:
            return
        cur = self.s.current
        i = next((k for k, (d, it) in enumerate(flat)
                  if cur and it is cur[1]), -1)
        i = max(0, min(len(flat) - 1, i + delta))
        self.select(*flat[i])

    def _picked(self, node, _prev):
        if node is None:
            return
        data = node.data(0, QtCore.Qt.UserRole)
        if data and data[0] == "item":
            self.s.set_current(data[1], data[2])

    def _renamed(self, node, column):
        data = node.data(0, QtCore.Qt.UserRole)
        if data and data[0] == "ds" and column == 0:
            new = node.text(0).strip()
            if new and new != data[1].name:
                data[1].name = new
                self.s.resultsChanged.emit()

    def _apply_filter(self, text):
        text = text.strip().lower()
        for k in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(k)
            for j in range(top.childCount()):
                node = top.child(j)
                node.setHidden(bool(text) and text not in node.text(0).lower())

    def _menu(self, pos):
        node = self.tree.itemAt(pos)
        if not node:
            return
        data = node.data(0, QtCore.Qt.UserRole)
        m = QtWidgets.QMenu(self)
        if data[0] == "ds":
            ds = data[1]
            m.addAction("Rename", lambda: self.tree.editItem(node, 0))
            m.addAction(f"Remove dataset {ds.name}", lambda: self.s.remove(ds))
        else:
            ds, it = data[1], data[2]
            m.addAction("Show in folder", lambda: QtGui.QDesktopServices.openUrl(
                QtCore.QUrl.fromLocalFile(os.path.dirname(it.path))))
            m.addAction(f"Remove {it.name}", lambda: self.s.remove(ds, it))
        m.exec(self.tree.viewport().mapToGlobal(pos))


class Console(QtWidgets.QPlainTextEdit):
    COLOURS = {"info": TEXT, "ok": PHOSPHOR, "warn": AMBER, "error": RED}

    def __init__(self, session):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        session.logged.connect(self.add)

    def add(self, level, msg):
        stamp = time.strftime("%H:%M:%S")
        col = self.COLOURS.get(level, TEXT)
        safe = (msg.replace("&", "&amp;").replace("<", "&lt;")
                   .replace(">", "&gt;"))
        self.appendHtml(f'<span style="color:{MUTED}">{stamp}</span>&nbsp;&nbsp;'
                        f'<span style="color:{col}">{safe}</span>')


class ExportDialog(QtWidgets.QDialog):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.setWindowTitle("Export")
        self.setMinimumWidth(560)
        st = QtCore.QSettings()
        lay = QtWidgets.QFormLayout(self)
        lay.setVerticalSpacing(10)

        self.out = QtWidgets.QLineEdit(st.value("export_dir", ""))
        lay.addRow("Output folder", self._browse(self.out))
        note = QtWidgets.QLabel("counts.csv (one row per run, every Batman "
                                "parameter and pickup measurement), spots.csv "
                                "(one row per spot) and params.json")
        note.setObjectName("muted")
        note.setWordWrap(True)
        lay.addRow("", note)
        self.marked = QtWidgets.QCheckBox("marked images, one per run")
        self.marked.setChecked(st.value("export_marked", True, type=bool))
        lay.addRow("", self.marked)

        self.master = QtWidgets.QCheckBox("append to the master archive")
        self.master.setChecked(st.value("export_master", False, type=bool))
        lay.addRow("", self.master)
        self.master_dir = QtWidgets.QLineEdit(st.value("master_dir", ""))
        self.master_row = self._browse(self.master_dir)
        lay.addRow("Master folder", self.master_row)
        self.replace = QtWidgets.QCheckBox(
            "replace runs already in the archive (otherwise they are skipped)")
        lay.addRow("", self.replace)
        self.master.toggled.connect(self._toggle)
        self._toggle(self.master.isChecked())

        if session.stale:
            warn = QtWidgets.QLabel("Settings changed since the last run all. "
                                    "The export uses the counted results, not "
                                    "the current sliders.")
            warn.setStyleSheet(f"color:{AMBER};")
            warn.setWordWrap(True)
            lay.addRow("", warn)

        bb = QtWidgets.QDialogButtonBox()
        go = bb.addButton("Export", QtWidgets.QDialogButtonBox.AcceptRole)
        go.setObjectName("primary")
        bb.addButton(QtWidgets.QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)

    def _browse(self, edit):
        w = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(edit, 1)
        b = QtWidgets.QPushButton("Browse…")
        b.clicked.connect(lambda: edit.setText(
            QtWidgets.QFileDialog.getExistingDirectory(self, "Choose folder",
                                                       edit.text()) or edit.text()))
        h.addWidget(b)
        return w

    def _toggle(self, on):
        self.master_row.setEnabled(on)
        self.replace.setEnabled(on)

    def _accept(self):
        if not self.out.text().strip():
            self.out.setFocus()
            return
        if self.master.isChecked() and not self.master_dir.text().strip():
            self.master_dir.setFocus()
            return
        st = QtCore.QSettings()
        st.setValue("export_dir", self.out.text().strip())
        st.setValue("export_marked", self.marked.isChecked())
        st.setValue("export_master", self.master.isChecked())
        st.setValue("master_dir", self.master_dir.text().strip())
        self.accept()

    def values(self):
        return (self.out.text().strip(), self.marked.isChecked(),
                self.master_dir.text().strip() if self.master.isChecked()
                else None, self.replace.isChecked())
