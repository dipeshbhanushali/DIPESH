"""
Hovering selects the explanation: which part of a panel is the mouse on?

A HoverWatch is installed on some widgets and everything inside them. On
every enter, leave or move it finds the widget under the cursor and walks up
to the first one it knows:

    keys       widget -> topic key
    resolvers  widget -> function(widget, local position) -> topic or None,
               for widgets whose parts mean different things (the cells and
               the header sections of a table)

and calls on_key with the topic, or with None when the mouse is on nothing
it knows.
"""

from PySide6 import QtCore, QtGui, QtWidgets


class HoverWatch(QtCore.QObject):

    def __init__(self, roots, on_key, keys=None, resolvers=None):
        super().__init__(roots[0])
        self.roots = list(roots)
        self.on_key = on_key
        self.keys = dict(keys or {})
        self.resolvers = dict(resolvers or {})
        self.entered = None
        self.last = object()
        for root in self.roots:
            for w in [root] + root.findChildren(QtWidgets.QWidget):
                w.installEventFilter(self)
        for w in self.resolvers:
            w.setMouseTracking(True)            # move events without a click
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self._resolve)

    def add(self, widget, key):
        self.keys[widget] = key

    def key_of(self, w, pos=None):
        while w is not None:
            if w in self.resolvers:
                p = w.mapFromGlobal(pos if pos is not None
                                    else QtGui.QCursor.pos())
                k = self.resolvers[w](w, p)
                if k is not None:
                    return k
            if w in self.keys:
                return self.keys[w]
            if w in self.roots:
                return None
            w = w.parentWidget()
        return None

    def eventFilter(self, obj, e):
        t = e.type()
        if t == QtCore.QEvent.Enter:
            self.entered = obj
            self.timer.start()
        elif t == QtCore.QEvent.Leave:
            if self.entered is obj:
                self.entered = None
            self.timer.start()
        elif t == QtCore.QEvent.MouseMove and obj in self.resolvers:
            self.entered = obj
            self.timer.start()
        return False

    def _resolve(self):
        # the widget under the cursor also catches moving from a control back
        # into the gap of its group, which sends no enter event; where there
        # is no window system to ask, the widget last entered stands in
        w = QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos())
        key = self.key_of(w if w is not None else self.entered)
        if key != self.last:
            self.last = key
            self.on_key(key)


def form_label(widget):
    """The label a QFormLayout put beside widget, if any."""
    p = widget.parentWidget()
    lay = p.layout() if p is not None else None
    if isinstance(lay, QtWidgets.QFormLayout):
        return lay.labelForField(widget)
    return None


def map_control(watch, widget, key):
    """A control, its caption above it and its label beside it: one topic."""
    watch.add(widget, key)
    cap = getattr(widget, "caption", None)
    if cap is not None:
        watch.add(cap, key)
        if cap.parentWidget() is not None:
            watch.add(cap.parentWidget(), key)   # the labelled() box
    lab = form_label(widget)
    if lab is not None:
        watch.add(lab, key)
