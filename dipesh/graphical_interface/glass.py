"""
The Glass theme's surfaces, at two intensities (View > Glass intensity):

  Subtle  a dark backdrop with a soft green/teal glow and a faint graticule;
          panels show a blurred copy of it under a dark translucent fill.
  Strong  (default) liquid glass: a deep dark base with large soft colour
          blobs (phosphor green, teal, a little violet) that drift slowly;
          panels are clear glass over a strong blur of them, with a white
          fill, a gradient border, a bright highlight along the top edge,
          rounded corners and a soft shadow. Menus and dialogs too.

Plot and image areas are never glass: they stay opaque, inside a glass
frame (Strong). Text contrast is checked against the lightest place each
surface can have (brightest_surfaces, tests/graphical_interface/test_themes).

Speed: the backdrop is drawn small and scaled up, and its blur is kept
tiny (each panel scales its own part); each panel's glass is drawn once into
a cached picture and only redrawn after a resize or an animation step. The
animation looks 15 times a second but redraws only when a blob has moved
MOVE_PX pixels (about 3 times a second), and not at all while live
detection or Run all is working, a mouse button is held, or for a second
after any key or mouse input: it never competes with the sliders.

On Windows 11 the window frame can also get the system's Mica backdrop and a
dark title bar (windows_frame); everywhere else that does nothing.
"""

import math
import sys
import time

from PySide6 import QtCore, QtGui, QtWidgets

INTENSITIES = ("Subtle", "Strong")

# ── Subtle (the first Glass look) ─────────────────────────────────────────
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

# ── Strong ────────────────────────────────────────────────────────────────
S_BASE_TOP = "#03070A"
S_BASE_BOTTOM = "#05080E"
# colour, centre (x, y) as a fraction of the window, radius as a fraction of
# its larger side, drift amplitude (x, y) as a fraction, phase
S_BLOBS = (
    ((60, 225, 110, 200), (0.22, 0.20), 0.42, (0.05, 0.035), 0.0),  # phosphor
    ((20, 175, 195, 190), (0.80, 0.78), 0.45, (0.04, 0.045), 2.1),  # teal
    ((135, 95, 230, 150), (0.86, 0.16), 0.32, (0.035, 0.04), 4.0),  # violet
    ((45, 200, 155, 150), (0.30, 0.92), 0.36, (0.045, 0.025), 5.3), # sea green
)
S_GRID = (190, 240, 215, 14)
S_SMALL = 8                            # the backdrop is drawn this much smaller
S_BLUR = 36                            # blur radius behind panels, px
S_TINT = (0, 0, 0, 225)                # darkens the blur under a panel,
                                       # so text keeps its contrast
S_FILL = (255, 255, 255, 20)           # white, ~8 %
S_SHEEN = (255, 255, 255, 10)          # extra white at the top, fading down
S_EDGE_TOP = (255, 255, 255, 90)       # border: ~35 % white at the top ...
S_EDGE_BOTTOM = (255, 255, 255, 20)    # ... ~8 % at the bottom
S_HIGHLIGHT = (255, 255, 255, 200)     # 1 px light along the top edge
S_RADIUS = 16
S_INSET = 10                           # panels float: backdrop all round
S_SHADOW = (0, 0, 0, 150)
S_SHADOW_BLUR = 14
S_SHADOW_DY = 6
S_FRAME_PAD = 5                        # glass frame around a plot
S_FRAME_FILL = (255, 255, 255, 14)
CYCLE = 60.0                           # s, one full drift
FPS = 15                               # how often the drift is looked at
MOVE_PX = 3.0                          # redraw after a blob moved this far
QUIET_S = 1.0                          # no redraw this long after input


def rgba(c):
    return QtGui.QColor(*c) if isinstance(c, tuple) else QtGui.QColor(c)


# ── drawing the backdrops ─────────────────────────────────────────────────

def render_backdrop(w, h):
    """The Subtle backdrop at w x h px: gradient, two glows, graticule."""
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


def blurred(img, by=BLUR):
    """A blurred copy: shrunk with smoothing, then grown back, twice."""
    w, h = img.width(), img.height()
    small = img.scaled(max(w // by, 1), max(h // by, 1),
                       QtCore.Qt.IgnoreAspectRatio,
                       QtCore.Qt.SmoothTransformation)
    small = small.scaled(max(w // (2 * by), 1), max(h // (2 * by), 1),
                         QtCore.Qt.IgnoreAspectRatio,
                         QtCore.Qt.SmoothTransformation)
    return small.scaled(w, h, QtCore.Qt.IgnoreAspectRatio,
                        QtCore.Qt.SmoothTransformation)


def blob_centres(w, h, t):
    """Where the Strong blobs are at time t (s): [(x, y, radius), ...]."""
    out = []
    a = 2 * math.pi * (t % CYCLE) / CYCLE
    big = max(w, h)
    for _c, (cx, cy), r, (ax, ay), ph in S_BLOBS:
        out.append(((cx + ax * math.sin(a + ph)) * w,
                    (cy + ay * math.cos(a + 1.3 * ph)) * h, r * big))
    return out


def render_strong(w, h, t):
    """The Strong backdrop at time t: (sharp, tiny). sharp is w x h: the
    blobs drawn S_SMALL times smaller and scaled up (they are soft anyway),
    the graticule sharp on top. tiny is the blur behind the panels, S_BLUR
    times smaller than the window, no graticule: scaled up smoothly it is
    the backdrop blurred by about S_BLUR px (soft_from)."""
    w, h = max(w, 1), max(h, 1)
    sw, sh = max(w // S_SMALL, 2), max(h // S_SMALL, 2)
    small = QtGui.QImage(sw, sh, QtGui.QImage.Format_RGB32)
    p = QtGui.QPainter(small)
    g = QtGui.QLinearGradient(0, 0, sw, sh)
    g.setColorAt(0, rgba(S_BASE_TOP))
    g.setColorAt(1, rgba(S_BASE_BOTTOM))
    p.fillRect(small.rect(), g)
    p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
    for (x, y, r), blob in zip(blob_centres(sw, sh, t), S_BLOBS):
        rg = QtGui.QRadialGradient(x, y, r)
        c = rgba(blob[0])
        for stop, k in ((0.0, 1.0), (0.35, 0.72), (0.7, 0.25), (1.0, 0.0)):
            cc = QtGui.QColor(c)
            cc.setAlpha(int(c.alpha() * k))
            rg.setColorAt(stop, cc)
        p.fillRect(small.rect(), rg)
    p.end()
    sharp = small.scaled(w, h, QtCore.Qt.IgnoreAspectRatio,
                         QtCore.Qt.SmoothTransformation)
    tiny = small.scaled(max(w // S_BLUR, 1), max(h // S_BLUR, 1),
                        QtCore.Qt.IgnoreAspectRatio,
                        QtCore.Qt.SmoothTransformation)
    p = QtGui.QPainter(sharp)
    p.setPen(QtGui.QPen(rgba(S_GRID), 1))
    for x in range(GRID_STEP // 2, w, GRID_STEP):
        p.drawLine(x, 0, x, h)
    for y in range(GRID_STEP // 2, h, GRID_STEP):
        p.drawLine(0, y, w, y)
    p.end()
    return sharp, tiny


def soft_from(tiny, w, h):
    """The full-size blur from the tiny one."""
    return tiny.scaled(w, h, QtCore.Qt.IgnoreAspectRatio,
                       QtCore.Qt.SmoothTransformation)


# ── colours and contrast ──────────────────────────────────────────────────

def over(top, bottom):
    """Colour of rgba top laid over an opaque bottom QColor."""
    t, a = rgba(top), rgba(top).alphaF()
    bottom = rgba(bottom)
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


def _lightest(img, step=4):
    img = img.convertToFormat(QtGui.QImage.Format_RGB32)
    best, best_l = None, -1.0
    for y in range(0, img.height(), step):
        for x in range(0, img.width(), step):
            c = img.pixelColor(x, y)
            lc = luminance(c)
            if lc > best_l:
                best, best_l = c, lc
    return best


def strong_panel(soft_colour):
    """A Strong panel's colour over one colour of the blurred backdrop."""
    return over(S_FILL, over(S_TINT, soft_colour))


def brightest_panel(w=1480, h=920):
    """The lightest colour a Subtle panel can have: the fill laid over the
    lightest pixel of the blurred backdrop."""
    return over(FILL, _lightest(blurred(render_backdrop(w, h))))


def brightest_strong_backdrop(w=1480, h=920, steps=12):
    """The lightest pixel of the blurred Strong backdrop over a whole drift
    cycle."""
    best, best_l = None, -1.0
    for k in range(steps):
        c = _lightest(render_strong(w, h, k * CYCLE / steps)[1], step=1)
        if luminance(c) > best_l:
            best, best_l = c, luminance(c)
    return best


# ── the window's central widget ───────────────────────────────────────────

def reduced_motion():
    """True when the system asks for less motion (Windows: "Animation
    effects" off). False where it cannot be asked."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        on = ctypes.c_int(1)
        ok = ctypes.windll.user32.SystemParametersInfoW(
            0x1042, 0, ctypes.byref(on), 0)      # SPI_GETCLIENTAREAANIMATION
        return bool(ok) and not on.value
    except Exception:                                  # noqa: BLE001
        return False


class Backdrop(QtWidgets.QWidget):
    """The window's central widget. With Glass on it paints the backdrop
    (and, Strong, the panels' shadows) and keeps a blurred copy for the
    panels; otherwise a flat colour. Strong can drift (animate())."""

    changed = QtCore.Signal()                 # the backdrop was redrawn

    def __init__(self, flat):
        super().__init__()
        self.glass = False
        self.intensity = "Strong"
        self.flat = flat
        self.panels = []                      # their shadows are drawn here
        self.version = 0
        self._key = None
        self.sharp = self.soft = None
        self._shadows = {}
        self.t = 0.0                          # drift time, s
        self.shown_t = 0.0                    # the time the backdrop shows
        self._clock = None
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(int(1000 / FPS))
        self.timer.timeout.connect(self._tick)
        self.frames = 0                       # redraws, for the tests
        self.tiny = None
        self._soft = None
        self.busy = lambda: False             # the window says when it works
        self.last_input = -1e9                # time of the last key or mouse

    @property
    def strong(self):
        return self.glass and self.intensity == "Strong"

    def _render(self):
        """Bring the backdrop up to date with the size, intensity and the
        drift time it shows."""
        key = (self.width(), self.height(), self.intensity,
               self.shown_t if self.intensity == "Strong" else None)
        if key != self._key:
            self._key = key
            if self.intensity == "Strong":
                self.sharp, self.tiny = render_strong(
                    self.width(), self.height(), self.shown_t)
                self._soft = None                 # made when asked for
            else:
                self.sharp = render_backdrop(self.width(), self.height())
                self._soft = blurred(self.sharp)
                self.tiny = None
            self.version += 1
            self.frames += 1

    def images(self):
        """(sharp, soft): the backdrop and its blur, both window size."""
        self._render()
        if self._soft is None:
            self._soft = soft_from(self.tiny, self.width(), self.height())
        return self.sharp, self._soft

    def blur_source(self):
        """(image, (fx, fy)): the blur behind the panels and the factors
        from window pixels to its pixels. Strong gives the tiny image, so
        no window-size copy is made at each drift step."""
        self._render()
        if self.tiny is not None:
            return self.tiny, (self.tiny.width() / max(self.width(), 1),
                               self.tiny.height() / max(self.height(), 1))
        return self._soft, (1.0, 1.0)

    # animation
    def animate(self, on):
        if on and self.strong:
            self._clock = time.monotonic()
            self.timer.start()
        else:
            self.timer.stop()

    def _moved(self, t0, t1):
        """Largest move of a blob between two times, in pixels."""
        a = blob_centres(self.width(), self.height(), t0)
        b = blob_centres(self.width(), self.height(), t1)
        return max(math.hypot(x0 - x1, y0 - y1)
                   for (x0, y0, _), (x1, y1, _) in zip(a, b))

    def _tick(self):
        now = time.monotonic()
        dt, self._clock = now - (self._clock or now), now
        if not self.strong or not self.isVisible():
            return
        self.t = (self.t + dt) % CYCLE
        if QtGui.QGuiApplication.mouseButtons() != QtCore.Qt.NoButton \
                or now - self.last_input < QUIET_S or self.busy():
            return                           # the user or the analysis first
        if self._moved(self.shown_t, self.t) < MOVE_PX:
            return
        self.shown_t = self.t
        self._render()
        self.update()
        self.changed.emit()

    # painting
    def _shadow(self, w, h):
        key = (w, h)
        if key not in self._shadows:
            pad = 2 * S_SHADOW_BLUR
            img = QtGui.QImage(w + 2 * pad, h + 2 * pad,
                               QtGui.QImage.Format_ARGB32_Premultiplied)
            img.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(img)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(rgba(S_SHADOW))
            p.drawRoundedRect(QtCore.QRectF(pad, pad, w, h), S_RADIUS, S_RADIUS)
            p.end()
            k = max(S_SHADOW_BLUR // 2, 1)
            small = img.scaled(max(img.width() // k, 1),
                               max(img.height() // k, 1),
                               QtCore.Qt.IgnoreAspectRatio,
                               QtCore.Qt.SmoothTransformation)
            self._shadows[key] = (small.scaled(img.width(), img.height(),
                                               QtCore.Qt.IgnoreAspectRatio,
                                               QtCore.Qt.SmoothTransformation),
                                  pad)
            if len(self._shadows) > 64:
                self._shadows.pop(next(iter(self._shadows)))
        return self._shadows[key]

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        if not self.glass:
            p.fillRect(e.rect(), rgba(self.flat))
            p.end()
            return
        self._render()
        p.drawImage(e.rect(), self.sharp, e.rect())
        if self.intensity == "Strong":
            for w in self.panels:
                if not w.isVisible():
                    continue
                r = QtCore.QRect(w.mapTo(self, QtCore.QPoint(0, 0)), w.size())
                r = r.adjusted(S_INSET, S_INSET, -S_INSET, -S_INSET)
                if r.width() < 4 or r.height() < 4:
                    continue
                img, pad = self._shadow(r.width(), r.height())
                at = r.topLeft() + QtCore.QPoint(-pad, -pad + S_SHADOW_DY)
                if e.rect().intersects(QtCore.QRect(at, img.size())):
                    p.drawImage(at, img)
        p.end()


# ── panels ────────────────────────────────────────────────────────────────

def strong_glass(p, rect, soft, src, radius=S_RADIUS, fill=S_FILL,
                 tint=S_TINT):
    """Draw one Strong glass shape into rect: the blurred backdrop part src
    (or none), darkened, a white fill, a sheen, the gradient border and the
    top highlight."""
    r = QtCore.QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)
    path = QtGui.QPainterPath()
    path.addRoundedRect(r, radius, radius)
    p.save()
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setClipPath(path)
    if soft is not None:
        p.drawImage(r, soft, QtCore.QRectF(src))
    if tint is not None:
        p.fillPath(path, rgba(tint))
    p.fillPath(path, rgba(fill))
    sheen = QtGui.QLinearGradient(0, r.top(), 0, r.top() + min(r.height(), 60))
    sheen.setColorAt(0, rgba(S_SHEEN))
    sheen.setColorAt(1, QtGui.QColor(255, 255, 255, 0))
    p.fillPath(path, sheen)
    p.setClipping(False)
    edge = QtGui.QLinearGradient(0, r.top(), 0, r.bottom())
    edge.setColorAt(0, rgba(S_EDGE_TOP))
    edge.setColorAt(1, rgba(S_EDGE_BOTTOM))
    p.setPen(QtGui.QPen(QtGui.QBrush(edge), 1))
    p.setBrush(QtCore.Qt.NoBrush)
    p.drawPath(path)
    line = QtGui.QLinearGradient(r.left(), 0, r.right(), 0)
    off = QtGui.QColor(*S_HIGHLIGHT[:3], 0)
    line.setColorAt(0, off)
    line.setColorAt(0.5, rgba(S_HIGHLIGHT))
    line.setColorAt(1, off)
    p.setPen(QtGui.QPen(QtGui.QBrush(line), 1))
    y = r.top() + 0.5
    p.drawLine(QtCore.QPointF(r.left() + radius * 0.6, y),
               QtCore.QPointF(r.right() - radius * 0.6, y))
    p.restore()


class Frost(QtCore.QObject):
    """Paints a glass panel under each widget it is installed on, before
    the widget draws itself, while the backdrop is in Glass mode. Strong
    panels are drawn once into a cached picture per widget, redrawn only
    when the widget's size or place or the backdrop changes."""

    def __init__(self, backdrop, widgets):
        super().__init__(backdrop)
        self.backdrop = backdrop
        self.widgets = list(widgets)
        backdrop.panels = self.widgets
        self._cache = {}
        self.rebuilds = 0                     # for the tests
        self.framed = []                      # callables -> widgets to frame
        self.extras = []                      # callables (w, painter) -> draw
        backdrop.changed.connect(self._backdrop_changed)
        for w in self.widgets:
            w.installEventFilter(self)

    def _backdrop_changed(self):
        for w in self.widgets:
            if w.isVisible():
                w.update()

    def eventFilter(self, w, e):
        if e.type() == QtCore.QEvent.Paint and self.backdrop.glass:
            if self.backdrop.intensity == "Strong":
                self.paint_strong(w, e.rect())
            else:
                self.paint(w)
        return False

    def paint(self, w):
        """The Subtle panel."""
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

    def picture(self, w):
        """The cached Strong panel of w."""
        blur, (fx, fy) = self.backdrop.blur_source()
        at = w.mapTo(self.backdrop, QtCore.QPoint(0, 0))
        dpr = w.devicePixelRatioF()
        key = (w.width(), w.height(), at.x(), at.y(), dpr,
               self.backdrop.version)
        hit = self._cache.get(w)
        if hit and hit[0] == key:
            return hit[1]
        pm = QtGui.QPixmap(int(w.width() * dpr), int(w.height() * dpr))
        pm.setDevicePixelRatio(dpr)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        rect = QtCore.QRect(0, 0, w.width(), w.height()).adjusted(
            S_INSET, S_INSET, -S_INSET, -S_INSET)
        r = QtCore.QRectF(rect.translated(at))
        src = QtCore.QRectF(r.x() * fx, r.y() * fy, r.width() * fx,
                            r.height() * fy)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        strong_glass(p, rect, blur, src)
        p.end()
        self._cache[w] = (key, pm)
        self.rebuilds += 1
        return pm

    def paint_strong(self, w, clip):
        pm = self.picture(w)
        p = QtGui.QPainter(w)
        k = pm.devicePixelRatio()
        p.drawPixmap(QtCore.QRectF(clip), pm,
                     QtCore.QRectF(clip.x() * k, clip.y() * k,
                                   clip.width() * k, clip.height() * k))
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        for get in self.framed:              # glass frames around plots
            for f in get(w):
                r = QtCore.QRect(f.mapTo(w, QtCore.QPoint(0, 0)), f.size())
                r = r.adjusted(-S_FRAME_PAD, -S_FRAME_PAD,
                               S_FRAME_PAD, S_FRAME_PAD)
                if r.intersects(clip):
                    strong_glass(p, r, None, None, fill=S_FRAME_FILL, tint=None)
        for draw in self.extras:
            draw(w, p)
        p.end()


def plot_frames(stack):
    """The plot and image views on show in a page, for their glass frames:
    an image view counts as one, with its histogram."""
    import pyqtgraph as pg

    def get(w):
        if w is not stack:
            return []
        out = []
        for v in stack.findChildren(pg.GraphicsView):
            if not v.isVisible():
                continue
            parent = v.parentWidget()
            while parent is not None and parent is not stack:
                if isinstance(parent, pg.ImageView):
                    v = parent
                    break
                parent = parent.parentWidget()
            if v not in out:
                out.append(v)
        return out
    return get


class PopupGlass(QtCore.QObject):
    """Strong glass for menus and dialogs, and the clock of the last key or
    mouse input that the drift waits for. It watches every event of the
    application, so it is installed only while Strong glass is on."""

    def __init__(self, backdrop):
        super().__init__(backdrop)
        self.backdrop = backdrop
        self.on = False

    def set_on(self, on):
        app = QtWidgets.QApplication.instance()
        if app is None or on == self.on:
            return
        if on:
            app.installEventFilter(self)
        else:
            app.removeEventFilter(self)
        self.on = on

    INPUT = (QtCore.QEvent.KeyPress, QtCore.QEvent.MouseButtonPress,
             QtCore.QEvent.MouseMove, QtCore.QEvent.Wheel)

    def eventFilter(self, obj, e):
        t = e.type()
        if t in self.INPUT:
            try:
                self.backdrop.last_input = time.monotonic()
            except RuntimeError:               # the window is gone
                pass
            return False
        if t not in (QtCore.QEvent.Polish, QtCore.QEvent.Paint):
            return False
        if not isinstance(obj, (QtWidgets.QMenu, QtWidgets.QDialog)):
            return False
        try:
            strong = self.backdrop.strong
        except RuntimeError:                   # the window is gone
            return False
        if not strong:
            return False
        if t == QtCore.QEvent.Polish:
            if isinstance(obj, QtWidgets.QMenu) and not obj.isVisible():
                obj.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            lay = obj.layout()
            if isinstance(obj, QtWidgets.QDialog) and lay is not None and                     not obj.property("glass_margins"):
                m = lay.contentsMargins()      # keep clear of the glass edge
                lay.setContentsMargins(m.left() + S_INSET, m.top() + S_INSET,
                                       m.right() + S_INSET, m.bottom() + S_INSET)
                obj.setProperty("glass_margins", True)
            return False
        if obj.isWindow():
            self.paint(obj, e.rect())
        return False

    def paint(self, w, clip):
        soft = self.backdrop.images()[1]
        at = self.backdrop.mapFromGlobal(w.mapToGlobal(QtCore.QPoint(0, 0)))
        src = QtCore.QRect(at, w.size())
        if not soft.rect().intersects(src):
            src = soft.rect()
        menu = isinstance(w, QtWidgets.QMenu)
        p = QtGui.QPainter(w)
        p.setClipRect(clip)
        if menu:
            p.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
            p.fillRect(w.rect(), QtCore.Qt.transparent)
            p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            strong_glass(p, w.rect().adjusted(1, 1, -1, -1), soft, src,
                         radius=12)
        else:
            p.fillRect(w.rect(), rgba(S_BASE_TOP))
            p.drawImage(QtCore.QRectF(w.rect()), soft, QtCore.QRectF(src))
            strong_glass(p, w.rect().adjusted(S_INSET, S_INSET,
                                              -S_INSET, -S_INSET),
                         soft, src.adjusted(S_INSET, S_INSET,
                                            -S_INSET, -S_INSET))
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
