"""spots: every spot's measurements, as a table."""

import csv
import math

from PySide6 import QtCore, QtGui, QtWidgets

from ..theme import AMBER, ISOLATED
from .base import Page, labelled


SPOT_COLS = [("spot", None), ("x", "x"), ("y", "y"),
             ("luminosity", "luminosity"), ("radius", "radius_used"),
             ("area", "area"), ("peak", "peak"), ("5x5 sum", "sum5x5"),
             ("radial σ", "radial_sigma"), ("concentration", "concentration"),
             ("eccentricity", "eccentricity"), ("slope", "profile_slope"),
             ("nearest", "nn_dist"), ("isolated", "is_isolated")]


class NumItem(QtWidgets.QTableWidgetItem):
    """Sorts by number, not by text."""

    def __init__(self, v, fmt):
        super().__init__(fmt.format(v) if isinstance(v, (int, float))
                         and math.isfinite(v) else ("∞" if v == float("inf")
                                                    else str(v)))
        self.v = v if isinstance(v, (int, float)) else 0
        self.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def __lt__(self, other):
        try:
            return float(self.v) < float(other.v)
        except (TypeError, ValueError, AttributeError):
            return super().__lt__(other)


class SpotsPage(Page):
    title = "spots"
    hint = "Every spot's measurements; double-click one to see it"
    uses_detection = True

    def __init__(self, session):
        super().__init__(session)
        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(8, 8, 8, 8)
        bar = QtWidgets.QHBoxLayout()
        self.scope = QtWidgets.QComboBox()
        self.scope.addItems(["this image (live settings)",
                             "whole dataset (last run all)"])
        bar.addWidget(labelled(self.scope, "spots from"))
        self.iso_only = QtWidgets.QCheckBox("isolated only")
        bar.addWidget(self.iso_only, 0, QtCore.Qt.AlignBottom)
        bar.addStretch(1)
        self.info = QtWidgets.QLabel("")
        self.info.setObjectName("muted")
        bar.addWidget(self.info, 0, QtCore.Qt.AlignBottom)
        save = QtWidgets.QPushButton("Save as CSV…")
        save.clicked.connect(self._save)
        bar.addWidget(save, 0, QtCore.Qt.AlignBottom)
        col.addLayout(bar)

        self.table = QtWidgets.QTableWidget(0, len(SPOT_COLS))
        self.table.setHorizontalHeaderLabels([c for c, _ in SPOT_COLS])
        self.table.verticalHeader().hide()
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._goto)
        col.addWidget(self.table, 1)

        self.scope.currentIndexChanged.connect(self.mark)
        self.iso_only.toggled.connect(self.mark)
        session.liveChanged.connect(self.mark)
        session.resultsChanged.connect(self.mark)
        session.currentChanged.connect(self.mark)

    def _rows(self):
        cur = self.s.current
        if not cur:
            return []
        if self.scope.currentIndex() == 0:
            r = self.s.live
            if r is None or not r.ok or r.item is not cur[1]:
                return []
            rows = [(r, k, s) for k, s in enumerate(r.spots)]
        else:
            rows = [(r, k, s) for r in cur[0].done()
                    for k, s in enumerate(r.spots)]
        if self.iso_only.isChecked():
            rows = [x for x in rows if x[2].is_isolated]
        return rows

    def refresh(self):
        rows = self._rows()
        whole = self.scope.currentIndex() == 1
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        fmts = {"luminosity": "{:.0f}", "peak": "{:.1f}", "sum5x5": "{:.0f}",
                "radial_sigma": "{:.2f}", "concentration": "{:.3f}",
                "eccentricity": "{:.3f}", "profile_slope": "{:.3f}",
                "nn_dist": "{:.1f}"}
        for i, (r, k, s) in enumerate(rows):
            if whole:
                first = QtWidgets.QTableWidgetItem(f"{r.item.name}:{k}")
            else:
                first = NumItem(k, "{}")
            self.table.setItem(i, 0, first)
            self.table.item(i, 0).setData(QtCore.Qt.UserRole, (r, s))
            for j, (_, attr) in enumerate(SPOT_COLS[1:], 1):
                v = getattr(s, attr)
                if attr == "is_isolated":
                    it = QtWidgets.QTableWidgetItem("yes" if v else "no")
                    it.setForeground(QtGui.QBrush(QtGui.QColor(
                        ISOLATED if v else AMBER)))
                    it.setTextAlignment(QtCore.Qt.AlignCenter)
                else:
                    it = NumItem(v, fmts.get(attr, "{}"))
                self.table.setItem(i, j, it)
        self.table.setSortingEnabled(True)
        n_iso = sum(1 for _, _, s in rows if s.is_isolated)
        self.info.setText(f"{len(rows)} spots, {n_iso} isolated" if rows else
                          ("run all to fill the dataset view" if whole
                           else ""))

    def _goto(self, row, _col):
        data = self.table.item(row, 0).data(QtCore.Qt.UserRole)
        if not data or not self.navigate:
            return
        r, s = data
        cur = self.s.current
        if cur and r.item is not cur[1]:
            self.s.set_current(cur[0], r.item)
        self.navigate("image", (s.x, s.y))

    def _save(self):
        rows = self._rows()
        if not rows:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save spots", "spots.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["run"] + [a for _, a in SPOT_COLS[1:]])
            for r, k, s in rows:
                w.writerow([r.item.name] + [getattr(s, a)
                                            for _, a in SPOT_COLS[1:]])
        self.s.log(f"saved {len(rows)} spots to {path}", "ok")
