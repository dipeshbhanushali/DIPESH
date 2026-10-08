"""dipesh/_about.py and CITATION.cff say the same thing."""
import os
import re

import dipesh
from dipesh import _about

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def read_cff(path):
    """The few fields we need from CITATION.cff, read line by line (the file
    is simple YAML; no YAML package needed). -> (fields, authors)"""
    def value(text):
        text = re.sub(r"\s+#.*$", "", text).strip()
        return text.strip('"').strip("'")

    fields, authors = {}, []
    in_authors = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            top = re.match(r"^([\w-]+):\s*(.*)$", line)
            if top:
                in_authors = top.group(1) == "authors"
                fields[top.group(1)] = value(top.group(2))
                continue
            item = re.match(r"^\s+(-\s+)?([\w-]+):\s*(.*)$", line)
            if in_authors and item:
                if item.group(1):
                    authors.append({})
                authors[-1][item.group(2)] = value(item.group(3))
    return fields, authors


CFF, CFF_AUTHORS = read_cff(os.path.join(ROOT, "CITATION.cff"))


def test_the_cff_reader_finds_the_fields():
    assert CFF["cff-version"] == "1.2.0" and len(CFF_AUTHORS) >= 1
    assert set(CFF_AUTHORS[0]) >= {"family-names", "given-names"}


def test_version_agrees_with_citation_cff_and_the_package():
    assert _about.VERSION == CFF["version"] == dipesh.__version__


def test_version_agrees_with_pyproject():
    with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as f:
        m = re.search(r'^version\s*=\s*"([^"]+)"', f.read(), re.M)
    assert m.group(1) == _about.VERSION


def test_release_date_agrees_with_citation_cff():
    assert _about.RELEASE_DATE == CFF["date-released"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", _about.RELEASE_DATE)


def test_title_agrees_with_citation_cff():
    assert _about.TITLE == CFF["title"]
    assert _about.TITLE.startswith(_about.NAME)


def test_authors_agree_with_citation_cff():
    assert len(_about.AUTHORS) == len(CFF_AUTHORS)
    for (given, family, orcid, aff), want in zip(_about.AUTHORS, CFF_AUTHORS):
        assert given == want["given-names"] and family == want["family-names"]
        assert orcid == want.get("orcid", "")
        assert aff == want.get("affiliation", "")


def test_licence_agrees_with_citation_cff():
    assert _about.LICENCE == CFF["license"]


def test_doi_agrees_with_citation_cff():
    assert (_about.DOI or "") == CFF.get("doi", "")
    if not _about.DOI:
        assert _about.doi_text() == "DOI: not yet assigned"


def test_the_about_lines_carry_every_field():
    text = " | ".join(f"{k}: {v}" for k, v in _about.about_lines())
    for piece in ([_about.VERSION, _about.RELEASE_DATE, _about.LICENCE,
                   _about.doi_text()] + _about.author_names()):
        assert piece in text
