"""
The words of the lessons, read from Markdown files in learn/texts/ while the
program runs.

A file is read again whenever it changes on disk, so an edit shows on the
next hover without restarting. The file explains its own format at the top:
one "## key" section per topic, with "title:", "shown:" and "legend:" lines,
then the explanation in Markdown. {name} is replaced by a live number.
"""

import os
import re

from PySide6 import QtCore

FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "texts")
FIELD = re.compile(r"\{(\w+)\}")


def legend_line(text):
    """"amber fill = pixels above the threshold" -> ("amber fill", "pixels
    above the threshold"); a line without "=" is a plain note."""
    mark, eq, meaning = text.partition("=")
    if not eq:
        return ("", text.strip())
    return (" ".join(mark.lower().split()), meaning.strip())


def parse(text):
    """-> {key: (title, shown, legend, body)} from the text of a lesson file;
    legend is a list of (mark, meaning)."""
    topics = {}
    key, lines = None, []

    def close():
        if key is None:
            return
        title, shown, legend, body = key, "", [], []
        head = True
        for ln in lines:
            if head and ln.lower().startswith("title:"):
                title = ln[6:].strip()
            elif head and ln.lower().startswith("shown:"):
                shown = ln[6:].strip()
            elif head and ln.lower().startswith("legend:"):
                legend.append(legend_line(ln[7:]))
            elif head and not ln.strip():
                continue
            else:
                head = False
                body.append(ln)
        topics[key] = (title, shown, legend, "\n".join(body).strip())

    for ln in text.splitlines():
        if ln.startswith("## "):
            close()
            key, lines = ln[3:].strip(), []
        elif key is not None:
            lines.append(ln)
    close()
    return topics


def fill(text, fields):
    """Put the live values in; a name with no value reads "–". Braces that
    hold anything but a plain name are left as they are."""
    return FIELD.sub(lambda m: str(fields.get(m.group(1), "–")), text)


class LessonText(QtCore.QObject):
    """One lesson file, kept up to date with the disk. changed is emitted
    when the file is saved, so the text on screen can be redrawn."""
    changed = QtCore.Signal()

    def __init__(self, name):
        super().__init__()
        self.path = os.path.join(FOLDER, name)
        self.topics = {}
        self.error = ""
        self._stamp = None
        self.watcher = QtCore.QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._on_disk)
        self.watcher.directoryChanged.connect(self._on_disk)
        if os.path.isdir(FOLDER):
            self.watcher.addPath(FOLDER)
        self._load()

    def _load(self):
        try:
            stamp = os.stat(self.path).st_mtime_ns
        except OSError:
            self.topics, self.error = {}, f"cannot find {self.path}"
            self._stamp = None
            return
        if stamp == self._stamp:
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                self.topics = parse(f.read())
            self.error = ""
        except (OSError, UnicodeDecodeError) as e:
            self.topics, self.error = {}, f"cannot read {self.path}: {e}"
        self._stamp = stamp
        # editors often save by replacing the file, which ends the watch
        if self.path not in self.watcher.files() and os.path.exists(self.path):
            self.watcher.addPath(self.path)

    def _on_disk(self, *_):
        old = self._stamp
        self._load()
        if self._stamp != old:
            self.changed.emit()

    def render(self, key, fields):
        """-> (title, shown, legend, markdown) for one topic, live values
        filled in; legend is a list of (mark, meaning)."""
        self._load()                             # in case a change was missed
        if self.error:
            return ("lesson text missing", "", [], f"**{self.error}**")
        if key not in self.topics:
            return (key, "", [], f"*No text for* `{key}` *in* "
                                 f"`{os.path.basename(self.path)}` *yet: add "
                                 f"a* `## {key}` *section.*")
        title, shown, legend, body = self.topics[key]
        return (fill(title, fields), fill(shown, fields),
                [(m, fill(t, fields)) for m, t in legend], fill(body, fields))
