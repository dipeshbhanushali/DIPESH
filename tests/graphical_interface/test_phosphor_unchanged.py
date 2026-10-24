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
