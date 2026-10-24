"""Phosphor stays exactly as it was: every page, pixel for pixel, against
pictures made before Glass "Strong" existed (tests/helpers/phosphor_shots.py),
and again after a trip through every Glass setting."""
import json
import os

import pytest
from PySide6 import QtGui

from phosphor_shots import REF, fill, shots, versions

with open(os.path.join(REF, "versions.json")) as f:
    MADE_WITH = json.load(f)


def same(img, name, tmp_path):
    want = QtGui.QImage(os.path.join(REF, f"{name}.png"))
    a = img.convertToFormat(QtGui.QImage.Format_RGB32)
    b = want.convertToFormat(QtGui.QImage.Format_RGB32)
    if a == b:
        return True
    a.save(str(tmp_path / f"{name}_now.png"))        # to look at
    return False


@pytest.fixture
def filled(window, data_root):
    if versions() != MADE_WITH:
        pytest.skip(f"reference pictures made with {MADE_WITH}, "
                    f"this is {versions()}")
    fill(window, data_root)
    return window


def test_every_phosphor_page_is_pixel_identical_to_before(filled, tmp_path):
    differ = [n for n, img in shots(filled).items()
              if not same(img, n, tmp_path)]
    assert not differ, f"changed: {differ} (see {tmp_path})"


def test_phosphor_is_the_same_after_every_glass_look(filled, monkeypatch):
    """Phosphor, then every Glass look, then Phosphor again: the same
    pixels. Both sets of pictures are taken once every page has been seen
    (the first visit of some pages draws later than the picture is taken,
    which the reference pictures show; that is page state, not the look)."""
    win = filled
    shots(win)                                   # every page seen once
    before = shots(win)
    clock = [0.0]
    from dipesh.graphical_interface import glass
    monkeypatch.setattr(glass.time, "monotonic", lambda: clock[0])
    for level in ("Subtle", "Strong"):
        win.set_glass_intensity(level, save=False)
        win.set_theme("Glass", save=False)
        # every page but learn: learn lines its sub-bar up under its tab
        # with a fixed spacer, so once shown in a wider window it keeps the
        # window that wide (as in 1.0). Glass is wider, so that would change
        # the window size, not the look. learn in Glass: test_themes.py.
        for k in range(len(win.pages) - 1):
            win.show_page(k)
        for _ in range(5):                       # let the background drift
            clock[0] += 3.0
            win.backdrop._tick()
        win.grab()
    win.set_theme("Phosphor", save=False)
    after = shots(win)
    differ = [n for n in before
              if before[n].convertToFormat(QtGui.QImage.Format_RGB32)
              != after[n].convertToFormat(QtGui.QImage.Format_RGB32)]
    assert not differ, f"changed: {differ}"
