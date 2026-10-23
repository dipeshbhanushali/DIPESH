"""
The look. Two themes, picked in View > Theme and kept in the settings:

  Phosphor  (default) a phosphor scope. A green-black tube face, faint green
            graticules on the plots, and the live count glowing P43 green
            (~545 nm) - the colour the MCP screen actually emits.
  Glass     the same colours for text, data and accents, on frosted panels
            over a dark backdrop with a soft green/teal glow (glass.py).
            Plot and image areas stay opaque.
"""

import os
import tempfile

import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from .._about import NAME as APP_NAME                    # noqa: F401

TUBE = "#0D1411"        # tube face: window background
PANEL = "#121B17"       # plot surfaces, lists
RAISED = "#17221D"      # buttons, headers
RULE = "#24352C"        # borders, graticule
TEXT = "#CFE3D6"        # phosphor afterglow white
MUTED = "#6F8A7B"
PHOSPHOR = "#9CFF57"    # P43 green — accents, the live count
SELECT = "#1E3A26"
AMBER = "#FFB547"       # crowded spots, warnings
ISOLATED = "#EAFFE0"    # isolated-spot rings: white reads on green phosphor
RED = "#FF6B6B"

# dataset colours (validated: lightness band, colour-blind separation and
# contrast on PANEL) + a marker shape each, so colour is never the only cue
SERIES = ["#21AC54", "#9A77EC", "#D97100", "#00A3C2", "#E7528C"]
SYMBOLS = ["o", "t", "s", "d", "star"]
# PicoScope channels: Pico's own blue (A) and amber (D); B and C changed
# because Pico's red/green pair is indistinguishable for deuteranopes
CHANNEL_COLOURS = {"A": "#00A3C2", "B": "#E7528C", "C": "#9A77EC", "D": "#D97100"}

MONO = '"Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace'

THEMES = ("Phosphor", "Glass")
# opaque plot and image areas, and their graticule, per theme
PLOT = {"Phosphor": PANEL, "Glass": "#0A1514"}
GRID_LINES = {"Phosphor": RULE, "Glass": "#1F3A33"}
_current = "Phosphor"


def current():
    """The theme in use: "Phosphor" or "Glass"."""
    return _current


def plot_background():
    return PLOT[_current]


def plot_rule():
    return GRID_LINES[_current]

QSS = f"""
* {{ font-family: {MONO}; font-size: 10pt; }}
QMainWindow, QWidget {{ background: {TUBE}; color: {TEXT}; }}
QToolTip {{ background: {RAISED}; color: {TEXT}; border: 1px solid {RULE};
            padding: 4px; }}

QFrame#bar {{ background: {TUBE}; border-bottom: 1px solid {RULE}; }}
QLabel#brand {{ color: {PHOSPHOR}; font-size: 13pt; font-weight: bold;
                padding: 0 18px 0 14px; }}
QLabel#brandsub {{ color: {MUTED}; padding-right: 14px; }}
QPushButton#nav {{ background: transparent; border: none; color: {MUTED};
                   padding: 11px 13px 9px 13px;
                   border-bottom: 2px solid transparent; }}
QPushButton#nav:hover {{ color: {TEXT}; }}
QPushButton#nav:checked {{ color: {PHOSPHOR}; border-bottom: 2px solid {PHOSPHOR}; }}
QToolButton#menu {{ background: transparent; border: none; color: {MUTED};
                    padding: 11px 13px 9px 13px;
                    border-bottom: 2px solid transparent; }}
QToolButton#menu:hover, QToolButton#menu:pressed {{ color: {TEXT}; }}
QToolButton#menu::menu-indicator {{ image: none; }}

QPushButton {{ background: {RAISED}; border: 1px solid {RULE}; color: {TEXT};
               padding: 5px 11px; border-radius: 3px; }}
QPushButton:hover {{ border-color: {PHOSPHOR}; }}
QPushButton:pressed {{ background: {SELECT}; }}
QPushButton:disabled {{ color: {MUTED}; border-color: {RULE}; }}
QPushButton:focus {{ border-color: {PHOSPHOR}; }}
QPushButton#primary {{ background: {PHOSPHOR}; color: {TUBE}; border: none;
                       font-weight: bold; padding: 6px 14px; }}
QPushButton#primary:hover {{ background: #B8FF85; }}
QPushButton#primary:disabled {{ background: {RULE}; color: {MUTED}; }}
QPushButton#stale {{ background: {AMBER}; color: {TUBE}; border: none;
                     font-weight: bold; padding: 6px 14px; }}

QGroupBox {{ border: 1px solid {RULE}; border-radius: 4px; margin-top: 14px;
             padding: 10px 8px 8px 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px;
                    color: {PHOSPHOR}; }}

QTreeWidget, QTableWidget, QPlainTextEdit, QListWidget {{
    background: {PANEL}; border: 1px solid {RULE};
    alternate-background-color: #141F1A; selection-background-color: {SELECT};
    selection-color: {PHOSPHOR}; outline: 0; }}
QTreeWidget::item, QListWidget::item {{ padding: 3px 2px; }}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {SELECT}; color: {PHOSPHOR}; }}
QHeaderView::section {{ background: {RAISED}; color: {MUTED}; border: none;
    border-bottom: 1px solid {RULE}; border-right: 1px solid {RULE};
    padding: 4px 6px; }}
QTableCornerButton::section {{ background: {RAISED}; border: none; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {PANEL}; border: 1px solid {RULE}; border-radius: 3px;
    padding: 3px 5px; selection-background-color: {SELECT}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {PHOSPHOR}; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {RULE};
    selection-background-color: {SELECT}; selection-color: {PHOSPHOR}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox {{ combobox-popup: 0; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 14px;
    background: {RAISED}; border: none; }}

QSlider::groove:horizontal {{ height: 3px; background: {RULE}; }}
QSlider::sub-page:horizontal {{ background: #4E8A2E; }}
QSlider::handle:horizontal {{ background: {PHOSPHOR}; width: 10px;
    height: 10px; margin: -4px 0; border-radius: 5px; }}
QSlider::handle:horizontal:hover {{ background: #C8FF9E; }}

QCheckBox {{ spacing: 7px; }}
QCheckBox::indicator {{ width: 12px; height: 12px; border: 1px solid {MUTED};
    background: {PANEL}; border-radius: 2px; }}
QCheckBox::indicator:checked {{ background: {PHOSPHOR};
    border-color: {PHOSPHOR}; }}

QProgressBar {{ border: 1px solid {RULE}; background: {PANEL}; height: 8px;
    border-radius: 2px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {PHOSPHOR}; }}

QScrollBar:vertical {{ background: {TUBE}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {RULE}; min-height: 24px;
    border-radius: 4px; }}
QScrollBar:horizontal {{ background: {TUBE}; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {RULE}; min-width: 24px;
    border-radius: 4px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QSplitter::handle {{ background: {RULE}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QMenu {{ background: {PANEL}; border: 1px solid {RULE}; }}
QMenu::item {{ padding: 5px 22px 5px 14px; }}
QMenu::item:selected {{ background: {SELECT}; color: {PHOSPHOR}; }}
QMenu::separator {{ height: 1px; background: {RULE}; margin: 4px 0; }}
QStatusBar {{ background: {TUBE}; color: {MUTED}; border-top: 1px solid {RULE}; }}
QTabWidget::pane {{ border: 1px solid {RULE}; }}
QTabBar::tab {{ background: {TUBE}; color: {MUTED}; padding: 5px 12px;
    border: 1px solid {RULE}; border-bottom: none; }}
QTabBar::tab:selected {{ color: {PHOSPHOR}; background: {PANEL}; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#heading {{ color: {PHOSPHOR}; font-weight: bold; }}
QLabel#count {{ color: {PHOSPHOR}; font-size: 40pt; font-weight: bold;
                background: transparent; }}
QLabel#brand, QLabel#brandsub {{ background: transparent; }}
QLabel#empty {{ color: {MUTED}; font-size: 11pt; }}
"""


def _arrow(path, colour, scale):
    """Draw the drop-down arrow (10 x 6 px, times scale) into a PNG."""
    pm = QtGui.QPixmap(10 * scale, 6 * scale)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setBrush(QtGui.QColor(colour))
    p.setPen(QtCore.Qt.NoPen)
    p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(0.5 * scale, 0.5 * scale),
                                   QtCore.QPointF(9.5 * scale, 0.5 * scale),
                                   QtCore.QPointF(5 * scale, 5.5 * scale)]))
    p.end()
    pm.save(path, "PNG")


def arrow_files():
    """Write the combo-box arrows (MUTED, and PHOSPHOR for hover) to the
    temp folder and return their paths. A Qt style sheet can only take the
    arrow from an image file; drawing it here keeps the colours in one place.
    Needs a running QApplication."""
    folder = os.path.join(tempfile.gettempdir(), "dipesh_theme")
    os.makedirs(folder, exist_ok=True)
    out = {}
    for name, colour in (("muted", MUTED), ("phosphor", PHOSPHOR)):
        out[name] = os.path.join(folder, f"arrow_{name}.png").replace("\\", "/")
        _arrow(out[name], colour, 1)
        _arrow(out[name].replace(".png", "@2x.png"), colour, 2)
    return out


# Glass: the Phosphor sheet with these rules after it. Widgets are clear so
# the frosted panels (glass.Frost) show; boxes, lists and fields get a
# translucent fill; pop-ups and dialogs, which have nothing of the window
# behind them, get the panel colour as a solid gradient.
_G_FIELD = "rgba(4, 10, 9, 150)"
_G_EDGE = "rgba(205, 255, 232, 40)"
_G_SELECT = "rgba(156, 255, 87, 40)"
_G_POP = "#0C1715"
GLASS_QSS = f"""
QMainWindow, QWidget {{ background: transparent; }}
QToolTip {{ background: {_G_POP}; border: 1px solid {_G_EDGE}; }}
QDialog {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 #0D1C18, stop:1 #0A1617); border: 1px solid {_G_EDGE}; }}
QFrame#bar {{ background: transparent; border: none; }}
QPushButton {{ background: rgba(23, 34, 29, 170); border: 1px solid {_G_EDGE};
               border-radius: 6px; }}
QPushButton:pressed {{ background: {_G_SELECT}; }}
QPushButton#nav {{ background: transparent; border: none;
                   border-bottom: 2px solid transparent; border-radius: 0; }}
QPushButton#nav:checked {{ border-bottom: 2px solid {PHOSPHOR}; }}
QPushButton#primary {{ background: {PHOSPHOR}; border: none; border-radius: 6px; }}
QPushButton#primary:hover {{ background: #B8FF85; }}
QPushButton#primary:disabled {{ background: {RULE}; }}
QPushButton#stale {{ background: {AMBER}; border: none; border-radius: 6px; }}
QGroupBox {{ border: 1px solid {_G_EDGE}; border-radius: 8px; }}
QTreeWidget, QTableWidget, QListWidget {{ background: {_G_FIELD};
    border: 1px solid {_G_EDGE}; border-radius: 6px;
    alternate-background-color: rgba(156, 255, 87, 8);
    selection-background-color: {_G_SELECT}; }}
QPlainTextEdit {{ background: transparent; border: none; }}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {_G_SELECT}; }}
QHeaderView::section {{ background: rgba(23, 34, 29, 200);
    border-bottom: 1px solid {_G_EDGE}; border-right: 1px solid {_G_EDGE}; }}
QTableCornerButton::section {{ background: rgba(23, 34, 29, 200); }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {_G_FIELD};
    border: 1px solid {_G_EDGE}; border-radius: 5px;
    selection-background-color: {_G_SELECT}; }}
QComboBox QAbstractItemView {{ background: {_G_POP}; border: 1px solid {_G_EDGE}; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: transparent; }}
QCheckBox::indicator {{ background: {_G_FIELD}; }}
QCheckBox::indicator:checked {{ background: {PHOSPHOR}; }}
QProgressBar {{ background: {_G_FIELD}; border: 1px solid {_G_EDGE}; }}
QScrollBar:vertical, QScrollBar:horizontal {{ background: transparent; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: rgba(205, 255, 232, 40); }}
QSplitter::handle {{ background: transparent; }}
QMenu {{ background: {_G_POP}; border: 1px solid {_G_EDGE}; }}
QMenu::item:selected {{ background: {_G_SELECT}; }}
QStatusBar {{ background: transparent; border-top: 1px solid {_G_EDGE}; }}
QTabWidget::pane {{ border: 1px solid {_G_EDGE}; border-radius: 6px; }}
QTabBar::tab {{ background: transparent; border: 1px solid {_G_EDGE};
    border-bottom: none; }}
QTabBar::tab:selected {{ background: {_G_SELECT}; }}
"""


def stylesheet(name=None):
    """The whole style sheet of a theme (the one in use if name is None):
    QSS (plus GLASS_QSS for Glass) and the combo-box arrows. Needs a
    running QApplication (the arrows are drawn with it).

    Keep the sub-control first in the selectors (::down-arrow:focus). Written
    the other way round (:focus::down-arrow) Qt draws a second arrow in the
    middle of the box."""
    a = arrow_files()
    glass = GLASS_QSS if (name or _current) == "Glass" else ""
    return QSS + glass + f"""
QComboBox {{ padding-right: 20px; }}
QComboBox::drop-down {{ subcontrol-origin: padding;
    subcontrol-position: center right; border: none; width: 20px; }}
QComboBox::down-arrow {{ image: url({a['muted']}); width: 10px; height: 6px; }}
QComboBox::down-arrow:hover, QComboBox::down-arrow:focus,
QComboBox::down-arrow:on {{ image: url({a['phosphor']}); }}
"""


def setup_pyqtgraph():
    pg.setConfigOptions(background=plot_background(), foreground=MUTED,
                        antialias=True, imageAxisOrder="row-major")


def use_theme(name, app=None):
    """Make name the theme in use: style sheet, pyqtgraph defaults. Plots
    that exist already are recoloured with restyle_plots()."""
    global _current
    if name not in THEMES:
        raise ValueError(f"no theme {name!r}; there are {THEMES}")
    _current = name
    app = app or QtWidgets.QApplication.instance()
    if app is not None:
        app.setStyleSheet(stylesheet(name))
    setup_pyqtgraph()


def restyle_plots(root):
    """Give every plot and image view under root the opaque background and
    the graticule of the theme in use."""
    for view in root.findChildren(pg.GraphicsView):
        view.setBackground(plot_background())
        for item in view.scene().items():
            if isinstance(item, pg.AxisItem):
                item.setPen(pg.mkPen(plot_rule()))
                item.setTextPen(pg.mkPen(MUTED))


def scope_plot(xlabel="", ylabel=""):
    """A plot styled as a scope screen: faint green graticule, quiet axes."""
    w = pg.PlotWidget()
    w.setBackground(plot_background())
    p = w.getPlotItem()
    p.showGrid(x=True, y=True, alpha=0.22)
    for name in ("left", "bottom"):
        ax = p.getAxis(name)
        ax.setPen(pg.mkPen(plot_rule()))
        ax.setTextPen(pg.mkPen(MUTED))
        ax.enableAutoSIPrefix(False)
    if xlabel:
        p.setLabel("bottom", xlabel, color=MUTED)
    if ylabel:
        p.setLabel("left", ylabel, color=MUTED)
    return w


def style_item(p):
    """Same graticule look for a PlotItem made inside a layout."""
    p.showGrid(x=True, y=True, alpha=0.22)
    for name in ("left", "bottom"):
        ax = p.getAxis(name)
        ax.setPen(pg.mkPen(plot_rule()))
        ax.setTextPen(pg.mkPen(MUTED))
        ax.enableAutoSIPrefix(False)
    return p


def glow(widget, colour=PHOSPHOR, radius=26):
    """Phosphor bloom on a label."""
    fx = QtWidgets.QGraphicsDropShadowEffect(widget)
    fx.setColor(QtGui.QColor(colour))
    fx.setBlurRadius(radius)
    fx.setOffset(0, 0)
    widget.setGraphicsEffect(fx)


def marker_icon(colour, symbol, size=12):
    """Small coloured marker, same shape as the dataset's plot marker."""
    pm = QtGui.QPixmap(size, size)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setBrush(QtGui.QColor(colour))
    p.setPen(QtCore.Qt.NoPen)
    s = size
    if symbol == "o":
        p.drawEllipse(1, 1, s - 2, s - 2)
    elif symbol == "s":
        p.drawRect(2, 2, s - 4, s - 4)
    elif symbol == "t":
        p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(s / 2, 1),
                                       QtCore.QPointF(s - 1, s - 1),
                                       QtCore.QPointF(1, s - 1)]))
    elif symbol == "d":
        p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(s / 2, 0),
                                       QtCore.QPointF(s, s / 2),
                                       QtCore.QPointF(s / 2, s),
                                       QtCore.QPointF(0, s / 2)]))
    else:
        p.drawEllipse(3, 3, s - 6, s - 6)
        p.setBrush(QtCore.Qt.NoBrush)
        p.setPen(QtGui.QPen(QtGui.QColor(colour), 1.4))
        p.drawEllipse(0, 0, s - 1, s - 1)
    p.end()
    return QtGui.QIcon(pm)
