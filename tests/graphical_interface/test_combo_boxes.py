"""Every drop-down looks like one (a visible arrow) and says above it what
it selects."""
import os
import re

from PySide6 import QtCore, QtGui, QtWidgets

from dipesh.graphical_interface import theme

CAPTIONS = {
    "image": {"colour map", "display mode"},
    "spots": {"spots from"},
    "histogram": {"feature", "lower dataset", "higher dataset"},
    "pca": {"axes"},
    "plots": {"x axis", "y axis", "error shown", "model"},
    "pickup": {"show", "channel"},
   
}
CAPTIONS["learn"] = set().union(*CAPTIONS.values())

def page_combos(page):
    """The page's own combo boxes (pyqtgraph's context menus have their own)."""
    return [c for c in page.findChildren(QtWidgets.QComboBox)
            if hasattr(c, "caption") or c.parent() is not None
            and "pyqtgraph" not in type(c.parent()).__module__]


def close_to(pixel, colour, tol=40):
    c = QtGui.QColor(colour)
    return (abs(pixel.red() - c.red()) + abs(pixel.green() - c.green())
            + abs(pixel.blue() - c.blue())) <= tol and pixel.alpha() > 200


def test_every_combo_box_has_a_label_above_it(window):
    for k, page in enumerate(window.pages):
        window.show_page(k)
        QtWidgets.QApplication.processEvents()
        combos = page_combos(page)
        assert {c.caption.text() for c in combos} == CAPTIONS[page.title]
        for c in combos:
            lab = c.caption
            assert lab.isVisible() and lab.objectName() == "muted"
            top = lab.mapTo(page, QtCore.QPoint(0, 0))
            box = c.mapTo(page, QtCore.QPoint(0, 0))
            assert top.y() + lab.height() <= box.y() + 1      # above
            assert abs(top.x() - box.x()) <= 2                # left edges agree


def test_the_combo_labels_look_like_the_other_small_headings(window):
    image = window.pages[0]
    ref = image.bat_label                            # "Batman parameters"
    lab = image.cmap.caption
    assert lab.font() == ref.font()
    assert (lab.palette().color(QtGui.QPalette.WindowText)
            == ref.palette().color(QtGui.QPalette.WindowText)
            == QtGui.QColor(theme.MUTED))


def test_the_style_sheet_points_at_arrow_images_that_exist(styled_app):
    qss = theme.stylesheet()
    urls = re.findall(r"down-arrow[^{]*\{ image: url\(([^)]+)\)", qss)
    assert len(urls) == 2 and urls[0] != urls[1]
    for url, colour in zip(urls, (theme.MUTED, theme.PHOSPHOR)):
        assert os.path.exists(url) and os.path.exists(url.replace(".png", "@2x.png"))
        img = QtGui.QImage(url)
        assert (img.width(), img.height()) == (10, 6)
        assert close_to(img.pixelColor(5, 2), colour, tol=6)


def arrow_pixels(combo, colour):
    """(pixels of that colour in the 20 px drop-down, and left of it,
    leaving out the 3 px border)."""
    QtWidgets.QApplication.processEvents()
    img = combo.grab().toImage()
    dpr = img.devicePixelRatio()
    w, h = combo.width(), combo.height()
    hit = lambda x, y: close_to(img.pixelColor(int(x * dpr), int(y * dpr)),
                                colour, tol=30)
    arrow = [(x, y) for x in range(w - 20, w - 3) for y in range(3, h - 3)
             if hit(x, y)]
    text_side = [(x, y) for x in range(3, w - 20) for y in range(3, h - 3)
                 if hit(x, y)]
    return arrow, text_side


def test_a_combo_box_is_drawn_with_a_visible_arrow(window):
    combo = window.pages[0].cmap
    window.pages[0].c_spots.setFocus()               # focus somewhere else
    arrow, text_side = arrow_pixels(combo, theme.MUTED)
    assert len(arrow) >= 12                          # a 10 x 6 px triangle
    assert not text_side                             # and only there
    xs = [x for x, _ in arrow]
    assert max(xs) - min(xs) >= 4                    # the soft edges do not match


def test_the_arrow_turns_phosphor_green_when_the_box_has_the_focus(window):
    combo = window.pages[0].cmap
    combo.setFocus()
    arrow, text_side = arrow_pixels(combo, theme.PHOSPHOR)
    assert len(arrow) >= 12
    assert not text_side                             # no second arrow in the box
