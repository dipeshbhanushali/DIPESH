"""
The overview: what each page of the program is for, and how the pages are
used together, in plain words. The first lesson of learn.

    left    a list of topics: the program, each page, a few workflows.
            Resting the mouse on one selects it; clicking keeps it.
    right   the description, from texts/overview.md
    below   "Open this page", for a topic that is a page of the program
"""

from PySide6 import QtCore, QtWidgets

from .description import Description
from .hover import HoverWatch

# (key, label, where "Open this page" goes: a main page title, "learn/<lesson>"
#  or None); a label starting with "—" is a group heading, not a topic
TOPICS = [
    ("—", "the program", None),
    ("program", "what DIPESH does", None),
    ("session", "a session, step by step", None),
    ("—", "the pages", None),
    ("image", "image", "image"),
    ("spots", "spots", "spots"),
    ("histogram", "histogram", "histogram"),
    ("pca", "pca", "pca"),
    ("plots", "plots", "plots"),
    ("pickup", "pickup", "pickup"),
    ("ions", "ions", "ions"),
    ("learn", "learn", "learn/image"),
    ("—", "workflows", None),
    ("wf_count", "count the antiprotons of a scan", "image"),
    ("wf_separate", "tell antiprotons from background", "histogram"),
    ("wf_tune", "tune and check the detection", "learn/image"),
    ("wf_pickup", "check the pickup signals", "pickup"),
]


class OverviewLesson(QtWidgets.QWidget):
    title = "overview"
    uses_detection = False

    def __init__(self, go):
        """go(target): opens a page of the program, or a learn lesson."""
        super().__init__()
        self.go = go
        self.topic = None            # under the mouse
        self.pinned = None           # clicked
        self.goto = {}

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)
        side = QtWidgets.QWidget()
        side.setFixedWidth(300)
        lay = QtWidgets.QVBoxLayout(side)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.buttons = {}
        keys = {}
        for key, label, target in TOPICS:
            if key == "—":
                h = QtWidgets.QLabel(label)
                h.setObjectName("heading")
                h.setContentsMargins(0, 10, 0, 2)
                lay.addWidget(h)
                continue
            b = QtWidgets.QPushButton(label)
            b.setCheckable(True)
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.setStyleSheet("text-align: left; padding: 5px 10px;")
            b.clicked.connect(lambda _=False, k=key: self.pin(k))
            lay.addWidget(b)
            self.buttons[key] = b
            self.goto[key] = target
            keys[b] = key
        lay.addStretch(1)
        row.addWidget(side)

        right = QtWidgets.QVBoxLayout()
        right.setSpacing(8)
        self.desc = Description("overview.md", shared=False)
        self.desc.connect_changed(self._draw)
        right.addWidget(self.desc, 1)
        self.open = QtWidgets.QPushButton("")
        self.open.setCursor(QtCore.Qt.PointingHandCursor)
        self.open.clicked.connect(self._open)
        self.open.hide()
        right.addWidget(self.open, 0, QtCore.Qt.AlignLeft)
        row.addLayout(right, 1)

        self.watch = HoverWatch([side], self.hovered, keys=keys)
        self.idle = QtCore.QTimer(self)
        self.idle.setSingleShot(True)
        self.idle.setInterval(250)
        self.idle.timeout.connect(self._leave)
        self._draw()

    @property
    def empty(self):
        return self.desc.heading       # always says something

    def showEvent(self, e):
        super().showEvent(e)
        self._draw()

    def hovered(self, key):
        if not self.isVisible():
            return
        if key is None:
            self.idle.start()
            return
        self.idle.stop()
        if key != self.topic:
            self.topic = key
            self._draw()

    def _leave(self):
        self.topic = None
        self._draw()

    def pin(self, key):
        self.pinned = None if self.pinned == key else key
        self._draw()

    def current(self):
        return self.topic or self.pinned

    def _open(self):
        target = self.goto.get(self.current())
        if target:
            self.go(target)

    def _draw(self, *_):
        key = self.current()
        for k, b in self.buttons.items():
            b.setChecked(k == self.pinned)
        self.desc.render(key or "intro", {})
        target = self.goto.get(key)
        if target:
            name = target.split("/")[1] if "/" in target else target
            where = f"learn / {name}" if "/" in target else f"the {name} page"
            self.open.setText(f"Open {where}")
            self.open.show()
        else:
            self.open.hide()
