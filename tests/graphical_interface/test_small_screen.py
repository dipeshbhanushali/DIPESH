"""The window fits a 1536 x 864 screen (1920 x 1080 at 125 %): every page,
in every look, with the settings panel open (it may scroll) and folded.
Measured in a process of its own with the system's fonts
(tests/helpers/fit_check.py)."""
import json
import os
import subprocess
import sys

import pytest

HELPER = os.path.join(os.path.dirname(__file__), "..", "helpers",
                      "fit_check.py")


def font_folder():
    for d in (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
              "/usr/share/fonts", "/System/Library/Fonts"):
        if os.path.isdir(d):
            return d
    return None


@pytest.fixture(scope="module")
def sizes():
    fonts = font_folder()
    if fonts is None:
        pytest.skip("no system fonts to measure text with")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QPA_FONTDIR=fonts,
               PYTHONUTF8="1")
    r = subprocess.run([sys.executable, HELPER], env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_every_page_fits_in_every_look_panel_open_and_folded(sizes):
    w, h = sizes["room"]
    pages = sizes["pages"]
    assert len(pages) == 3 * 2 * 8
    too_big = [p for p in pages if p["min"][0] > w or p["min"][1] > h]
    assert not too_big, too_big
    # and resized to the room, the window stays inside it
    grown = [p for p in pages if p["size"][0] > w or p["size"][1] > h]
    assert not grown, grown


def test_folding_the_panel_gives_the_picture_room(sizes):
    # the same window, the panel folded to its strip: the rest is the picture's
    by = {(p["look"], p["panel"], p["page"]): p["panel_width"]
          for p in sizes["pages"]}
    for look in ("Phosphor Strong", "Glass Strong"):
        for page in ("image", "ions"):
            assert by[(look, False, page)] <= 20
            assert by[(look, True, page)] > 200


def test_the_settings_panel_folds_from_view_and_its_button_and_is_kept(
        window, qtbot):
    from PySide6 import QtCore
    ions = next(p for p in window.pages if p.title == "ions")
    assert window.panel_action.isChecked()                     # open at first
    assert window.right.area.isVisible()
    window.panel_action.trigger()                              # View: fold
    assert not window.right.is_open and not ions.side.is_open
    assert not window.right.area.isVisible()
    assert QtCore.QSettings().value("settings_panel", type=bool) is False
    ions.side.button.click()                    # the arrow on the Ions page
    assert window.right.is_open and window.panel_action.isChecked()
    window.right.button.click()                 # the arrow on the image page
    assert not ions.side.is_open and not window.panel_action.isChecked()
    from dipesh.graphical_interface.main_window import MainWindow
    again = MainWindow()                        # a new start: still folded
    qtbot.addWidget(again)
    assert not again.right.is_open and not again.panel_action.isChecked()
    again.close()
    again.deleteLater()
