"""
What the program says about itself: name, version, authors, release date,
licence, DOI. The About window and __version__ read it from here.

Keep it equal to CITATION.cff (tests/test_about.py checks that). It is a
Python file, not the .cff, so that the packaged app carries it.
"""

NAME = "DIPESH"
TITLE = "DIPESH — Detection and Imaging of Pbar Events, Spots and Hits"
VERSION = "1.0.0"
RELEASE_DATE = "2026-10-08"

# (given names, family names, ORCID, affiliation); "" where there is none
AUTHORS = [
    ("Dipesh", "Bhanushali", "", ""),
]

LICENCE = "GPL-3.0-or-later"
DOI = None                       # set when Zenodo has assigned one

DESCRIPTION = "Antiproton counting and data analysis tool, built by Dipesh Bhanushali."


def author_names():
    """["Given Family", ...]"""
    return [f"{given} {family}" for given, family, _orcid, _aff in AUTHORS]


def doi_text():
    return f"DOI: {DOI}" if DOI else "DOI: not yet assigned"


def about_lines():
    """[(label, text), ...] for the About window, in order."""
    return [
        ("Version", VERSION),
        ("Released", RELEASE_DATE),
        ("Authors" if len(AUTHORS) > 1 else "Author",
         ", ".join(f"{name} ({aff})" if aff else name
                   for name, (_g, _f, _o, aff)
                   in zip(author_names(), AUTHORS))),
        ("Licence", LICENCE),
        ("Cite", doi_text()),
    ]
