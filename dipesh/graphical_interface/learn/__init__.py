"""
learn — the seventh analysis on the top bar, next to pickup: lessons that
explain what the program does, one subpanel per analysis.

    page          LearnPage, the panel the main window shows, and its sub-bar
    image_lesson  the image subpanel: what each setting and feature computes
    settings      learn's own detection settings, and Apply
    crops         the pipeline stages and the event / background windows
    textfile      reads the lesson texts from texts/*.md, live
    texts/        the lesson texts, Markdown, to edit
"""


def __getattr__(name):
    # loaded on first use: the page imports the graphical interface, which
    # imports this package, and the non-GUI modules here must not need Qt
    if name == "LearnPage":
        from .page import LearnPage
        return LearnPage
    raise AttributeError(name)
