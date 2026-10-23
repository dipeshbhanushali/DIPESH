"""
The Glass theme's surfaces: a dark backdrop with a soft green/teal glow and a
faint graticule, and frosted panels over it. A panel shows a blurred copy of
the backdrop behind it, a translucent fill, a 1 px light border and rounded
corners. Plot and image areas are not panels: they stay opaque.

On Windows 11 the window frame can also get the system's Mica backdrop and a
dark title bar (windows_frame); everywhere else that does nothing.
"""

import sys

from PySide6 import QtCore, QtGui, QtWidgets

# (r, g, b, alpha) unless a plain colour
BASE_TOP = "#050C0B"
BASE_BOTTOM = "#061214"
GLOW_GREEN = (46, 200, 130, 70)        # soft, top left
GLOW_TEAL = (24, 160, 180, 60)         # soft, bottom right
GRID = (140, 230, 190, 10)             # the graticule, every GRID_STEP px
GRID_STEP = 44
FILL = (10, 20, 18, 205)               # panel fill over the blurred backdrop
BORDER = (205, 255, 232, 42)           # 1 px light edge
RADIUS = 10
INSET = 3                              # gap between a panel and its edge
BLUR = 18                              # blur: shrink by this, then grow back


def rgba(c):
    return QtGui.QColor(*c) if isinstance(c, tuple) else QtGui.QColor(c)


def render_backdrop(w, h):
    """The backdrop at w x h px: gradient, two glows, graticule."""
    img = QtGui.QImage(max(w, 1), max(h, 1), QtGui.QImage.Format_RGB32)
    p = QtGui.QPainter(img)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    g = QtGui.QLinearGradient(0, 0, w, h)
    g.setColorAt(0, rgba(BASE_TOP))
    g.setColorAt(1, rgba(BASE_BOTTOM))
    p.fillRect(img.rect(), g)
    big = max(w, h)
    for (cx, cy), colour in (((0.18, 0.10), GLOW_GREEN),
                             ((0.88, 0.92), GLOW_TEAL)):
        r = QtGui.QRadialGradient(cx * w, cy * h, 0.65 * big)
        c = rgba(colour)
        r.setColorAt(0, c)
        c.setAlpha(0)
        r.setColorAt(1, c)
        p.fillRect(img.rect(), r)
    p.setPen(QtGui.QPen(rgba(GRID), 1))
    for x in range(GRID_STEP // 2, w, GRID_STEP):
        p.drawLine(x, 0, x, h)
    for y in range(GRID_STEP // 2, h, GRID_STEP):
        p.drawLine(0, y, w, y)
    p.end()
    return img


def blurred(img):
    """A blurred copy: shrunk with smoothing, then grown back, twice."""
    w, h = img.width(), img.height()
    small = img.scaled(max(w // BLUR, 1), max(h // BLUR, 1),
                       QtCore.Qt.IgnoreAspectRatio,
                       QtCore.Qt.SmoothTransformation)
    small = small.scaled(max(w // (2 * BLUR), 1), max(h // (2 * BLUR), 1),
                         QtCore.Qt.IgnoreAspectRatio,
                         QtCore.Qt.SmoothTransformation)
    return small.scaled(w, h, QtCore.Qt.IgnoreAspectRatio,
                        QtCore.Qt.SmoothTransformation)


def over(top, bottom):
    """Colour of rgba top laid over an opaque bottom QColor."""
    t, a = rgba(top), rgba(top).alphaF()
    return QtGui.QColor(*(round(a * tc + (1 - a) * bc) for tc, bc in
                          ((t.red(), bottom.red()), (t.green(), bottom.green()),
                           (t.blue(), bottom.blue()))))


def luminance(c):
    """Relative luminance (WCAG 2)."""
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    c = rgba(c)
    return 0.2126 * lin(c.red()) + 0.7152 * lin(c.green()) + 0.0722 * lin(c.blue())


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def brightest_panel(w=1480, h=920):
    """The lightest colour a frosted panel can have: the fill laid over the
    lightest pixel of the blurred backdrop. Text on panels is checked
    against it."""
    img = blurred(render_backdrop(w, h)).convertToFormat(
        QtGui.QImage.Format_RGB32)
    best, best_l = None, -1.0
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            c = img.pixelColor(x, y)
            lc = luminance(c)
            if lc > best_l:
                best, best_l = c, lc
    return over(FILL, best)


class Backdrop(QtWidgets.QWidget):
    """The window's central widget. With Glass on it paints the backdrop
    and keeps a blurred copy for the panels; otherwise a flat colour."""

    def __init__(self, flat):
        super().__init__()
        self.glass = False
        self.flat = flat
        self._size = None
        self.sharp = self.soft = None

    def images(self):
        if self._size != self.size():
            self._size = self.size()
            self.sharp = render_backdrop(self.width(), self.height())
            self.soft = blurred(self.sharp)
        return self.sharp, self.soft

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        if self.glass:
            p.drawImage(e.rect(), self.images()[0], e.rect())
        else:
            p.fillRect(e.rect(), rgba(self.flat))
        p.end()


class Frost(QtCore.QObject):
    """Paints a frosted panel under each widget it is installed on, before
    the widget draws itself, while the backdrop is in Glass mode."""

    def __init__(self, backdrop, widgets):
        super().__init__(backdrop)
        self.backdrop = backdrop
        self.widgets = list(widgets)
        for w in self.widgets:
            w.installEventFilter(self)

    def eventFilter(self, w, e):
        if e.type() == QtCore.QEvent.Paint and self.backdrop.glass:
            self.paint(w)
        return False

    def paint(self, w):
        soft = self.backdrop.images()[1]
        p = QtGui.QPainter(w)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = QtCore.QRectF(w.rect()).adjusted(INSET + 0.5, INSET + 0.5,
                                            -INSET - 0.5, -INSET - 0.5)
        path = QtGui.QPainterPath()
        path.addRoundedRect(r, RADIUS, RADIUS)
        p.setClipPath(path)
        at = w.mapTo(self.backdrop, QtCore.QPoint(0, 0))
        p.drawImage(QtCore.QPoint(0, 0), soft, QtCore.QRect(at, w.size()))
        p.fillPath(path, rgba(FILL))
        p.setClipping(False)
        p.setPen(QtGui.QPen(rgba(BORDER), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawPath(path)
        p.end()


def windows_frame(widget, glass):
    """Windows 11: a dark title bar and the Mica backdrop on the window frame
    with Glass on; the system default with it off. Anywhere else (Windows 10,
    other systems, the offscreen test platform) nothing happens.
    -> True if Windows took the setting."""
    if sys.platform != "win32" or \
            QtGui.QGuiApplication.platformName() != "windows":
        return False
    try:
        if sys.getwindowsversion().build < 22000:      # Windows 10
            return False
        import ctypes
        set_attr = ctypes.windll.dwmapi.DwmSetWindowAttribute
        hwnd = ctypes.c_void_p(int(widget.winId()))
        dark = ctypes.c_int(1 if glass else 0)
        kind = ctypes.c_int(2 if glass else 0)         # 2 Mica, 0 default
        a = set_attr(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
        b = set_attr(hwnd, 38, ctypes.byref(kind), ctypes.sizeof(kind))
        return a == 0 and b == 0
    except Exception:                                  # noqa: BLE001
        return False
