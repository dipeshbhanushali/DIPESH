"""
The settings the learn panel tries out, apart from the analysis.

learn has its own detection panel: the same widget as the main window's,
bound to a session of its own that follows the run selected in the main
list. Moving its sliders re-detects the frame for the lesson only. Nothing
reaches the image page and the analysis until Apply is pressed.
"""

from PySide6 import QtCore, QtWidgets

from ..session import Session
from ..theme import AMBER, muted
from ..widgets import DetectionPanel
from ..workers import LiveDetector

WARNING = "Press to apply settings for the analysis"


def panel_keys(panel):
    """widget -> topic key for every part of a DetectionPanel the mouse can
    rest on; the keys of the image lesson's texts."""
    k = {panel.count: "count", panel.count_sub: "count"}
    for key, value in panel.facts.items():
        k[value] = key
    # the names of the facts sit in the same grid row as their values
    for lay in _layouts(panel.layout()):
        if isinstance(lay, QtWidgets.QGridLayout):
            for r in range(lay.rowCount()):
                a, b = lay.itemAtPosition(r, 0), lay.itemAtPosition(r, 1)
                if a and b and b.widget() in k:
                    k[a.widget()] = k[b.widget()]
    for key, w in {**panel.w, **panel.w2}.items():
        k[w] = key
    k[panel.adaptive] = "adaptive"
    for box in panel.findChildren(QtWidgets.QGroupBox):
        k[box] = "detection" if box.title() == "detection" else "measurement"
    return k


def _layouts(lay):
    """A layout and every layout nested in it."""
    if lay is None:
        return []
    out = [lay]
    for i in range(lay.count()):
        sub = lay.itemAt(i).layout()
        if sub is not None:
            out += _layouts(sub)
    return out


class LearnSettings(QtCore.QObject):
    """A private session, its live detector, and its detection panel with
    the Apply button. apply(params) hands the settings to the analysis."""

    def __init__(self, main, apply):
        super().__init__()
        self.main = main
        self._apply = apply
        self.s = Session()
        self.s.params = main.params
        self.base = main.params                  # the analysis's, last seen
        self.live = LiveDetector(self.s)
        self.s.logged.connect(main.logged)      # Save… / Load… messages
        main.currentChanged.connect(self._follow)
        main.paramsChanged.connect(self._state)
        self.s.paramsChanged.connect(self._state)

        self.panel = DetectionPanel(self.s)
        self.panel.set_params(main.params)
        col = self.panel.layout()
        at = col.count() - 1                     # above Reset / Save / Load
        self.warning = QtWidgets.QLabel(WARNING)
        self.warning.setAlignment(QtCore.Qt.AlignCenter)
        self.warning.setWordWrap(True)
        self.button = QtWidgets.QPushButton("Apply")
        self.button.setObjectName("primary")
        self.button.setMinimumHeight(44)
        f = self.button.font()
        f.setPointSizeF(f.pointSizeF() * 1.3)
        self.button.setFont(f)
        self.button.setCursor(QtCore.Qt.PointingHandCursor)
        self.button.setToolTip("Use these settings on the image page and for "
                               "Run all. Until then they only change this "
                               "lesson.")
        self.button.clicked.connect(self.apply)
        col.insertWidget(at, self.warning)
        col.insertWidget(at + 1, self.button)
        col.insertSpacing(at + 2, 6)
        self._follow()
        self._state()

    def _follow(self):
        """Show the run selected in the main list."""
        cur = self.main.current
        self.s.set_current(*(cur if cur else (None, None)))

    @property
    def pending(self):
        """True while these settings differ from the analysis's."""
        return self.s.params != self.main.params

    def _state(self, *_):
        p = self.pending
        self.button.setEnabled(p)
        self.warning.setStyleSheet(f"color: {AMBER if p else muted()};")
        self.warning.setToolTip("These settings differ from the analysis's"
                                if p else "These are the analysis's settings")

    def sync(self):
        """Catch up with settings changed on the image page, unless there
        are changes here still waiting to be applied."""
        if self.main.params != self.base:
            if self.s.params == self.base:
                self.panel.set_params(self.main.params)
            self.base = self.main.params
        self._state()

    def apply(self):
        self._apply(self.s.params)
        self.base = self.main.params
        self.main.log("learn: settings applied to the analysis", "ok")
        self._state()
