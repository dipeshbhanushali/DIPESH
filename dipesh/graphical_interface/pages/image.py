"""image: the current frame, every counted spot drawn at its true aperture,
settings live."""

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from ...single_image_analysis import (load_item, prepare, remove_hot_pixels,
                                      to_float)
from ..theme import AMBER, ISOLATED, MUTED, PHOSPHOR, RULE, TEXT
from .base import Page, empty_overlay, labelled, qcolor


def phosphor_map():
    """Black → P43 green → white: the image looks like the screen itself."""
    return pg.ColorMap([0.0, 0.35, 0.75, 1.0],
                       [(4, 8, 6), (22, 92, 34), (156, 255, 87),
                        (240, 255, 230)])


COLORMAPS = {
    "phosphor": phosphor_map,
    "inferno": lambda: pg.colormap.get("inferno"),
    "viridis": lambda: pg.colormap.get("viridis"),
    "jet": lambda: pg.colormap.get("jet", source="matplotlib"),
    "grey": lambda: pg.ColorMap([0, 1], [(0, 0, 0), (255, 255, 255)]),
}


class ImagePage(Page):
    title = "image"
    hint = "The current frame with every counted spot, settings live"
    uses_detection = True

    def __init__(self, session):
        super().__init__(session)
        self._img = None
        self._img_path = None

        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(8, 8, 8, 8)
        col.setSpacing(6)

        top = QtWidgets.QHBoxLayout()
        self.where = QtWidgets.QLabel("")
        self.where.setObjectName("heading")
        top.addWidget(self.where)
        top.addStretch(1)
        self.cursor = QtWidgets.QLabel("")
        self.cursor.setObjectName("muted")
        top.addWidget(self.cursor)
        col.addLayout(top)

        opts = QtWidgets.QHBoxLayout()
        self.cmap = QtWidgets.QComboBox()
        self.cmap.addItems(list(COLORMAPS))
        self.cmap.setToolTip("Colour map — display only")
        opts.addWidget(labelled(self.cmap, "colour map"))
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(["camera image", "background subtracted"])
        self.mode.setToolTip("Background subtracted is what the detector "
                             "actually thresholds")
        opts.addWidget(labelled(self.mode, "display mode"))
        self.c_spots = QtWidgets.QCheckBox("spots")
        self.c_spots.setChecked(True)
        self.c_mcp = QtWidgets.QCheckBox("MCP boundary")
        self.c_mcp.setChecked(True)
        self.c_lock = QtWidgets.QCheckBox("keep levels")
        self.c_lock.setToolTip("Keep the same display levels when you move "
                               "between images, for comparing them")
        # the check boxes sit on the line of the combo boxes, under the labels
        for c in (self.c_spots, self.c_mcp, self.c_lock):
            opts.addWidget(c, 0, QtCore.Qt.AlignBottom)
        opts.addStretch(1)
        key = QtWidgets.QLabel(f'<span style="color:{ISOLATED}">◯</span> '
                               f'isolated &nbsp;&nbsp; <span style="color:'
                               f'{AMBER}">◯</span> crowded')
        key.setObjectName("muted")
        key.setToolTip("Each circle is the aperture the spot's light was "
                       "summed over")
        key.setMinimumWidth(1)        # a narrow window may cut the legend
        opts.addWidget(key, 0, QtCore.Qt.AlignBottom)
        col.addLayout(opts)

        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.view = pg.ImageView()
        self.view.ui.roiBtn.hide()
        self.view.ui.menuBtn.hide()
        self.vb = self.view.getView()
        self.vb.invertY(True)
        self.vb.setAspectLocked(True)
        self.view.setColorMap(phosphor_map())
        hist = self.view.getHistogramWidget().item
        hist.plot.setPen(pg.mkPen(PHOSPHOR, width=1))
        hist.plot.setBrush(qcolor(PHOSPHOR, 45))
        hist.region.setBrush(qcolor(PHOSPHOR, 22))
        hist.axis.setPen(pg.mkPen(RULE))
        hist.axis.setTextPen(pg.mkPen(MUTED))

        self.iso = pg.ScatterPlotItem(pxMode=False, brush=None,
                                      pen=pg.mkPen(ISOLATED, width=1.6))
        self.crowd = pg.ScatterPlotItem(pxMode=False, brush=None,
                                        pen=pg.mkPen(AMBER, width=1.6))
        self.vb.addItem(self.iso)
        self.vb.addItem(self.crowd)
        self.mcp = QtWidgets.QGraphicsEllipseItem()
        pen = QtGui.QPen(QtGui.QColor(TEXT), 1.2, QtCore.Qt.DotLine)
        pen.setCosmetic(True)
        self.mcp.setPen(pen)
        self.vb.addItem(self.mcp)
        split.addWidget(self.view)

        bat = QtWidgets.QWidget()
        bl = QtWidgets.QVBoxLayout(bat)
        bl.setContentsMargins(0, 0, 0, 0)
        self.bat_label = QtWidgets.QLabel("Batman parameters")
        self.bat_label.setObjectName("muted")
        bl.addWidget(self.bat_label)
        self.batman = QtWidgets.QTableWidget(0, 2)
        self.batman.setHorizontalHeaderLabels(["parameter", "value"])
        self.batman.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.Stretch)
        self.batman.verticalHeader().hide()
        self.batman.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.batman.setAlternatingRowColors(True)
        bl.addWidget(self.batman)
        split.addWidget(bat)
        split.setSizes([640, 140])
        col.addWidget(split, 1)

        self.empty = empty_overlay(self.view, "Add a folder of runs to start.\n"
                                   "Ctrl+O, or drop a folder on the list.")

        self.cmap.currentTextChanged.connect(
            lambda n: self.view.setColorMap(COLORMAPS[n]()))
        self.mode.currentIndexChanged.connect(lambda *_: self._show(True))
        self.c_spots.toggled.connect(self._overlays)
        self.c_mcp.toggled.connect(self._overlays)
        self.view.scene.sigMouseMoved.connect(self._mouse)

        session.currentChanged.connect(self._load)
        session.liveChanged.connect(self._overlays)
        session.paramsChanged.connect(self._params_changed)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.empty.setGeometry(self.view.rect())

    def _load(self):
        cur = self.s.current
        self.empty.setVisible(cur is None)
        if not cur:
            self.view.clear()
            self.where.setText("")
            self.batman.setRowCount(0)
            return
        ds, it = cur
        self.where.setText(f"{ds.name}  /  {it.name}")
        self._img = load_item(it)
        self._img_path = it.key
        self._show(not self.c_lock.isChecked())
        self._overlays()

    def _params_changed(self):
        if self.mode.currentIndex() == 1 or self.s.params.hotpix_delta:
            self._show(False)

    def _show(self, reset_levels):
        if self._img is None:
            return
        p = self.s.params
        if self.mode.currentIndex() == 1:
            shown = prepare(self._img, p)[0]
        else:
            shown = to_float(remove_hot_pixels(self._img, p)[0])
        levels = None if reset_levels else self.view.getLevels()
        first = self.view.image is None
        self.view.setImage(shown, autoRange=first, autoLevels=False,
                           autoHistogramRange=reset_levels)
        if levels is not None and not reset_levels:
            self.view.setLevels(*levels)
        else:
            # one bright pixel would bury every faint spot under min/max
            # scaling; a percentile stretch shows them. Display only.
            lo = float(np.percentile(shown, 1.0))
            hi = float(np.percentile(shown, 99.95))
            self.view.setLevels(lo, hi if hi > lo else lo + 1)

    def _overlays(self, *_):
        r = self.s.live
        cur = self.s.current
        valid = (r is not None and r.ok and cur is not None
                 and r.item is cur[1] and self.c_spots.isChecked())
        for item, keep in ((self.iso, True), (self.crowd, False)):
            if not valid:
                item.setData([])
                continue
            sp = [s for s in r.spots if s.is_isolated == keep]
            item.setData(x=[s.x for s in sp], y=[s.y for s in sp],
                         size=[2 * s.radius_used + 3 for s in sp])
        reg = self.s.params.mcp_region
        if reg and self.c_mcp.isChecked() and cur:
            cx, cy, rr = reg
            self.mcp.setRect(cx - rr, cy - rr, 2 * rr, 2 * rr)
            self.mcp.show()
        else:
            self.mcp.hide()
        if valid:
            bat = r.batman
            self.bat_label.setText(f"Batman parameters ({len(bat)})" if bat
                                   else "no Batman.json for this image")
            self.batman.setRowCount(len(bat))
            for k, key in enumerate(sorted(bat)):
                self.batman.setItem(k, 0, QtWidgets.QTableWidgetItem(key))
                v = QtWidgets.QTableWidgetItem(f"{bat[key]:g}")
                v.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.batman.setItem(k, 1, v)

    def _mouse(self, pos):
        if self.view.image is None:
            return
        pt = self.vb.mapSceneToView(pos)
        x, y = int(pt.x()), int(pt.y())
        img = self.view.image
        if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
            self.cursor.setText(f"x {x:4d}   y {y:4d}   value {img[y, x]:7.1f}")
        else:
            self.cursor.setText("")

    def focus(self, x, y, half=45):
        self.vb.setRange(xRange=(x - half, x + half),
                         yRange=(y - half, y + half), padding=0)
