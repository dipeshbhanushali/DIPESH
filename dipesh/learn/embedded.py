"""
A main page living inside a lesson.

The lesson builds the real page (so its controls and plots are exactly the
ones of the page), takes its widgets into its own layout, and is told after
every redraw so it can add its explanations on top.
"""


def embedded(page_class):
    """A subclass of page_class that redraws when its lesson is visible
    (the page widget itself is never shown) and calls after() each time."""

    class Embedded(page_class):

        def __init__(self, session, host, after):
            self.host = host
            self.after = after
            super().__init__(session)

        def mark(self, *_):
            self._dirty = True
            if self.host.isVisible():
                self.shown()

        def refresh(self):
            super().refresh()
            self.after()

    Embedded.__name__ = f"Learn{page_class.__name__}"
    return Embedded


def take(page):
    """The page's widgets, left to right, taken out of its layout."""
    lay = page.layout()
    out = []
    while lay.count():
        w = lay.takeAt(0).widget()
        if w is not None:
            out.append(w)
    return out
