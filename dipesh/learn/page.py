"""learn: lessons on what the program computes, one subpanel per analysis.

Its own bar of tabs (overview, image, spots, histogram, pca) sits just under the top
bar, starting below the "learn" tab, the way a sub-menu hangs from its menu.
"""

from PySide6 import QtCore, QtWidgets

from ..graphical_interface.pages.base import Page
from .histogram_lesson import HistogramLesson
from .hover import HoverWatch
from .image_lesson import ImageLesson
from .overview_lesson import OverviewLesson
from .pca_lesson import PcaLesson
from .settings import LearnSettings, panel_keys
from .spots_lesson import SpotsLesson


class LearnPage(Page):
    title = "learn"
    hint = "What the program computes, explained on your own data"
    # learn has its own settings panel; the main window's stays hidden
    uses_detection = False

    def __init__(self, session):
        super().__init__(session)
        self.settings = LearnSettings(session, self._apply)
        col = QtWidgets.QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        self.subbar = QtWidgets.QFrame()
        self.subbar.setObjectName("bar")
        hb = QtWidgets.QHBoxLayout(self.subbar)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(0)
        self.indent = QtWidgets.QSpacerItem(0, 0)
        hb.addItem(self.indent)
        self.sub = QtWidgets.QButtonGroup(self)
        self.sub.setExclusive(True)
        ls = self.settings.s
        self.lessons = [OverviewLesson(self.go), ImageLesson(ls),
                        SpotsLesson(ls, session), HistogramLesson(session),
                        PcaLesson(session)]
        self.stack = QtWidgets.QStackedWidget()
        for k, lesson in enumerate(self.lessons):
            b = QtWidgets.QPushButton(lesson.title)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.setToolTip(f"learn what the {lesson.title} page computes")
            self.sub.addButton(b, k)
            hb.addWidget(b)
            self.stack.addWidget(lesson)
        hb.addStretch(1)
        self.sub.idClicked.connect(self.show_lesson)
        col.addWidget(self.subbar)

        # learn's detection panel sits on the right, as on the image and
        # spots pages, for the lessons of those pages
        body = QtWidgets.QWidget()
        bl = QtWidgets.QHBoxLayout(body)
        bl.setContentsMargins(8, 8, 0, 8)
        bl.setSpacing(10)
        bl.addWidget(self.stack, 1)
        panel = self.settings.panel
        bl.addWidget(panel)
        col.addWidget(body, 1)
        self.panel_watch = HoverWatch([panel], self._panel_hover,
                                      keys=panel_keys(panel))
        self.sub.button(0).setChecked(True)
        self.show_lesson(0)

    @property
    def lesson(self):
        return self.stack.currentWidget()

    @property
    def empty(self):
        return self.lesson.empty

    def show_lesson(self, k):
        self.sub.button(k).setChecked(True)
        self.stack.setCurrentIndex(k)
        self.settings.panel.setVisible(self.lesson.uses_detection)

    def _panel_hover(self, key):
        """The mouse on learn's detection panel: the lesson on show explains."""
        lesson = self.lesson
        if lesson.uses_detection:
            getattr(lesson, "panel_hovered", lesson.hovered)(key)

    def go(self, target):
        """Open a page of the program ("image") or a lesson ("learn/image")."""
        if target.startswith("learn/"):
            name = target.split("/", 1)[1]
            k = next((i for i, l in enumerate(self.lessons) if l.title == name),
                     None)
            if k is not None:
                self.show_lesson(k)
        elif self.navigate:
            self.navigate(target)

    def _apply(self, params):
        """Hand learn's settings to the analysis: the main detection panel
        takes them, exactly as if its own sliders had been moved."""
        main = getattr(self.window(), "detection", None)
        if main is not None:
            main.set_params(params)
        else:
            self.s.set_params(params)

    def shown(self):
        self.settings.sync()
        self._align()
        super().shown()

    def _align(self):
        """Start the sub-bar right under the "learn" tab of the top bar."""
        win = self.window()
        nav = getattr(win, "nav", None)
        pages = getattr(win, "pages", [])
        if nav is None or self not in pages:
            return
        tab = nav.button(pages.index(self))
        x = tab.mapTo(win, QtCore.QPoint(0, 0)).x() - \
            self.mapTo(win, QtCore.QPoint(0, 0)).x()
        room = self.width() - sum(self.sub.button(k).sizeHint().width()
                                  for k in range(len(self.lessons)))
        x = max(0, min(x, room))
        self.indent.changeSize(x, 0)
        self.subbar.layout().invalidate()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._align()
