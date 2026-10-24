"""
The description section every lesson has: a heading and the text of the
topic the mouse rests on, read live from the lesson's Markdown file.

{about} in a lesson text is replaced by the section of texts/features.md
that defines the feature the topic is about, so a feature is defined once
and every lesson uses the same words.
"""

from PySide6 import QtCore, QtWidgets

from .textfile import LessonText

_features = None


def features():
    """texts/features.md, shared by every lesson (made once Qt runs)."""
    global _features
    if _features is None:
        _features = LessonText("features.md")
    return _features


class Description(QtWidgets.QWidget):
    """Heading + text + where the text comes from."""

    def __init__(self, filename, shared=True):
        """shared: the texts may use {about} from features.md."""
        super().__init__()
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.heading = QtWidgets.QLabel("")
        self.heading.setObjectName("heading")
        self.heading.setWordWrap(True)
        lay.addWidget(self.heading)
        self.text = QtWidgets.QTextBrowser()
        self.text.setOpenLinks(False)
        lay.addWidget(self.text, 1)
        self.words = LessonText(filename)
        files = f"{filename} and features.md" if shared else filename
        src = QtWidgets.QLabel(f"text from learn/texts/{files} — save and the "
                               f"change shows here")
        src.setObjectName("muted")
        src.setWordWrap(True)
        src.setToolTip(self.words.path)
        lay.addWidget(src)

    def connect_changed(self, slot):
        self.words.changed.connect(slot)
        features().changed.connect(slot)

    def render(self, key, fields, feature=None):
        """Show one topic; -> (shown, legend) for the figure's legend."""
        f = dict(fields)
        if feature:
            _, _, _, about = features().render(feature, fields)
            f["about"] = about
        title, shown, legend, body = self.words.render(key, f)
        self.heading.setText(title)
        self.text.setMarkdown(body)
        return shown, legend


def feature_meaning(feature):
    """The one-line meaning of a feature: the "shown:" line of its section
    in features.md."""
    return features().render(feature, {})[1]
