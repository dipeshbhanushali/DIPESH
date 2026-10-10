"""The window opens and every page can be reached, with and without data."""
from PySide6 import QtCore

from gui import run_all, show

PAGES = ["image", "spots", "histogram", "pca", "plots", "pickup", "learn"]


def test_the_window_opens_on_the_image_page_with_seven_pages(window):
    assert window.isVisible()
    assert [p.title for p in window.pages] == PAGES
    assert window.stack.currentIndex() == 0
    assert window.nav.button(0).isChecked()
    assert "DIPESH" in window.windowTitle()


def test_each_page_is_selected_from_the_top_bar(window, qtbot):
    for k in (6, 5, 4, 3, 2, 1, 0):
        qtbot.mouseClick(window.nav.button(k), QtCore.Qt.LeftButton)
        assert window.stack.currentIndex() == k
        assert window.stack.currentWidget() is window.pages[k]
        assert window.pages[k].isVisible()
        # the detection panel belongs to the image and spots pages only
        assert window.detection.isVisible() == (k < 2)


def test_each_page_is_selected_with_ctrl_and_its_number(window, qtbot):
    for k in (6, 5, 4, 3, 2, 1, 0):
        qtbot.keyClick(window, str(k + 1), QtCore.Qt.ControlModifier)
        assert window.stack.currentIndex() == k
        assert window.nav.button(k).isChecked()


def test_without_data_every_page_says_what_to_do(window, qtbot):
    for title in PAGES:
        page = show(window, title)
        if title == "spots":
            assert page.table.rowCount() == 0
        else:
            if title == "pickup":                    # drawn after a short delay
                qtbot.wait(250)
            assert page.empty.isVisible() and page.empty.text()
    assert window.detection.count.text() == "\u2013"
    assert not window.run_btn.isEnabled() and not window.export_btn.isEnabled()


def test_with_data_every_page_shows_it(loaded, qtbot):
    win = loaded
    run_all(win, qtbot)
    ds, item = win.s.current
    n_spots = win.s.live.n

    image = show(win, "image")
    assert image.view.image is not None and not image.empty.isVisible()
    assert image.where.text() == f"{ds.name}  /  {item.name}"
    drawn = len(image.iso.getData()[0]) + len(image.crowd.getData()[0])
    assert drawn == n_spots
    assert image.batman.rowCount() == len(win.s.live.batman) == 4

    spots = show(win, "spots")
    assert spots.table.rowCount() == n_spots
    spots.scope.setCurrentIndex(1)                   # whole dataset
    assert spots.table.rowCount() == sum(r.n for r in ds.done())

    hist = show(win, "histogram")
    assert not hist.empty.isVisible()
    assert len(hist.plot.getPlotItem().listDataItems()) == 3   # one per dataset
    assert "separation score" in hist.stats.text()

    pca = show(win, "pca")
    assert not pca.empty.isVisible()
    assert len(pca.scatter.getPlotItem().items) >= 3
    assert "variance" in pca.stats.text()

    plots = show(win, "plots")
    assert not plots.empty.isVisible()
    assert plots.x.currentData() == "ExtLine_TrapBiasGround"   # the scan
    assert plots.y.currentData() == "pbar_count"
    assert len(plots.plot.getPlotItem().listDataItems()) >= 3

    pickup = show(win, "pickup")
    qtbot.waitUntil(lambda: bool(pickup.traces), timeout=30000)
    assert not pickup.empty.isVisible()


def test_the_about_window_shows_what_about_py_says(window, monkeypatch):
    from PySide6 import QtWidgets
    from dipesh import _about
    seen = {}
    monkeypatch.setattr(QtWidgets.QMessageBox, "about",
                        lambda parent, title, text: seen.update(title=title,
                                                                text=text))
    window.help_menu.actions()[-1].trigger()         # Help > About
    assert seen["title"] == f"About {_about.NAME}"
    for piece in ([_about.TITLE, _about.VERSION, _about.RELEASE_DATE,
                   _about.LICENCE, "DOI: not yet assigned"]
                  + _about.author_names()):
        assert piece in seen["text"], piece
    for label in ("Version", "Released", "Author", "Licence", "Cite"):
        assert label in seen["text"]


def test_the_shortcuts_window_lists_the_keys(window, monkeypatch):
    from PySide6 import QtWidgets
    seen = {}
    monkeypatch.setattr(QtWidgets.QMessageBox, "information",
                        lambda parent, title, text: seen.update(keys=text))
    window._keys()
    for key in ("Ctrl+1", "PgUp", "Ctrl+O", "Ctrl+R", "Ctrl+E", "Ctrl+Q"):
        assert key in seen["keys"]


def test_the_top_bar_shows_the_version(window):
    import dipesh
    from PySide6 import QtWidgets
    labels = [w.text() for w in window.findChildren(QtWidgets.QLabel)]
    assert f"v{dipesh.__version__}" in labels
