
NAME = "DIPESH"
TITLE = "DIPESH — Detection and Imaging of Pbar Events, Spots and Hits"
VERSION = "2.0.0.dev0"
RELEASE_DATE = "2026-10-08"

# (given names, family names, ORCID, affiliation); 
AUTHORS = [
    ("Dipesh", "Bhanushali", "https://orcid.org/0009-0004-2631-6684",""),
    ("Giovanni", "Cerchiari", "https://orcid.org/0000-0003-3068-0425",""),
]

LICENCE = "GPL-3.0-or-later"
DOI = "10.5281/zenodo.23286325"                      #

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
