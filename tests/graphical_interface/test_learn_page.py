"""The learn page lines its sub-bar up under its tab, without holding the
window wide."""
from PySide6 import QtWidgets


def test_the_window_can_shrink_again_after_learn_was_shown_wide(window):
    learn = window.pages[-1]
    QtWidgets.QApplication.processEvents()
    narrow = learn.minimumSizeHint().width()
    window.show_page(len(window.pages) - 1)
    window.resize(window.width() + 700, window.height())
    QtWidgets.QApplication.processEvents()
    assert learn.indent.sizeHint().width() > 0          # lined up under its tab
    assert learn.minimumSizeHint().width() == narrow    # but not held wide
    window.show_page(0)
    wide = window.width()
    window.resize(window.minimumSizeHint().width(), window.height())
    QtWidgets.QApplication.processEvents()
    assert window.width() < wide
