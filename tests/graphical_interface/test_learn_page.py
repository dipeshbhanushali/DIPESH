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


def test_the_overview_has_every_page_with_a_text_and_opens_it(window):
    from dipesh.graphical_interface.learn.overview_lesson import TOPICS
    learn = window.pages[-1]
    overview = learn.lessons[0]
    pages = [p.title for p in window.pages]
    pages_listed = [k for k, _, _ in TOPICS if k in pages]
    assert pages_listed == pages                    # every page, in order
    for key, label, _ in TOPICS:
        if key == "—":
            continue
        overview.pin(key)
        assert overview.desc.heading.text().startswith(label.split(" ")[0]) \
            or overview.desc.heading.text().startswith("workflow"), key
        assert len(overview.desc.text.toPlainText()) > 100, key
        overview.pin(key)                           # unpin
    window.show_page(len(pages) - 1)
    overview.pin("ions")
    assert overview.open.text() == "Open the ions page"
    overview.open.click()
    assert window.stack.currentWidget().title == "ions"
