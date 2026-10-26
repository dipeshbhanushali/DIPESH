"""What every page shares: the Page class and small layout helpers."""

import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from ..theme import PANEL, RULE, TEXT

FEATURE_LABELS = {
    "luminosity": "luminosity",
    "peak": "peak",
    "sum5x5": "5x5 sum",
    "radial_sigma": "radial σ",
    "area": "aperture area",
    "concentration": "concentration",
    "eccentricity": "eccentricity",
    "profile_slope": "profile slope",
    "nn_dist": "nearest-neighbour distance",
}
LOG_BY_DEFAULT = {"luminosity", "peak", "sum5x5"}


def qcolor(hex_, alpha=255):
    c = QtGui.QColor(hex_)
    c.setAlpha(alpha)
    return c


def side_column(width=290):
    """A page's column of controls at the right, width px wide; it scrolls
    when the window is too short for it. -> (column, its layout)"""
    w = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(w)
    lay.setContentsMargins(10, 10, 10, 10)
    lay.setSpacing(8)
    area = QtWidgets.QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QtWidgets.QFrame.NoFrame)
    area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    area.setWidget(w)
    area.setFixedWidth(width)
    return area, lay


def combo(items=()):
    """A combo box that shrinks to its panel instead of widening it."""
    c = QtWidgets.QComboBox()
    c.setSizeAdjustPolicy(
        QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
    c.setMinimumContentsLength(8)
    c.addItems(list(items))
    return c


def labelled(widget, text):
    """The widget with a small muted label above it saying what it selects.
    Every combo box on the pages gets one."""
    box = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    lab = QtWidgets.QLabel(text)
    lab.setObjectName("muted")
    lab.setBuddy(widget)
    lay.addWidget(lab)
    lay.addWidget(widget)
    widget.caption = lab
    return box


def form(parent_layout, title):
    box = QtWidgets.QGroupBox(title)
    f = QtWidgets.QFormLayout(box)
    f.setLabelAlignment(QtCore.Qt.AlignLeft)
    f.setHorizontalSpacing(10)
    f.setVerticalSpacing(5)
    parent_layout.addWidget(box)
    return f


def add_legend(plot):
    leg = plot.addLegend(offset=(-12, 10), brush=pg.mkBrush(qcolor(PANEL, 220)),
                         pen=pg.mkPen(RULE), labelTextColor=TEXT)
    return leg


def empty_overlay(parent, text):
    lab = QtWidgets.QLabel(text, parent)
    lab.setObjectName("empty")
    lab.setAlignment(QtCore.Qt.AlignCenter)
    lab.setWordWrap(True)
    lab.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
    return lab


class Page(QtWidgets.QWidget):
    title = ""
    hint = ""
    uses_detection = False

    def __init__(self, session):
        super().__init__()
        self.s = session
        self._dirty = True
        self.navigate = None             # set by the main window

    def mark(self, *_):
        self._dirty = True
        if self.isVisible():
            self.shown()

    def shown(self):
        if self._dirty:
            self._dirty = False
            self.refresh()

    def refresh(self):
        pass
