"""report/make_report.py writes a .tex that lists every test.

The report script is run here with --quick (it then runs only the fast
analysis tests itself, not the whole suite again) and --no-pdf.
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "report", "make_report.py")


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    out = tmp_path_factory.mktemp("report")
    r = subprocess.run([sys.executable, SCRIPT, "--no-pdf", "--quick",
                        "--out", str(out)], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stdout + r.stderr
    with open(out / "report.tex", encoding="utf-8") as f:
        return out, f.read()


def collected():
    """Every test name of the suite, as pytest lists them."""
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q",
                        "-p", "no:cacheprovider"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return [l.strip() for l in r.stdout.splitlines()
            if "::" in l and not l.startswith(" ")]


def test_the_report_contains_every_test_name(report):
    _, tex = report
    names = collected()
    assert len(names) > 200
    missing = [n for n in names if n not in tex]
    assert not missing, missing[:5]


def test_the_report_has_its_title_version_and_sections(report):
    from dipesh import _about
    _, tex = report
    assert "test report" in tex and f"version {_about.VERSION}" in tex
    # the commit is printed when the folder is a git repository with one,
    # and says so when the working copy has local edits; the version may
    # carry a suffix such as .dev0
    assert re.search(r"version [\w.]+(, commit [0-9a-f]{7,40}"
                     r"( \(with uncommitted changes\))?)?\\\\", tex)
    assert r"\usepackage{mathpazo}" in tex
    for title in ("Summary", "Luminosity", "Radial sigma", "Concentration",
                  "Eccentricity", "Profile slope", "Isolation",
                  "Pickup: RF notch", "All tests"):
        assert r"\section{" + title + "}" in tex, title
    assert "2\\pi A \\sigma^2" in tex                # a formula
    assert "sqrt(2) sigma" in tex                    # from a test docstring


def test_the_report_gives_true_measured_error_and_tolerance(report):
    _, tex = report
    assert "case & true & measured & relative error & tolerance" in tex
    assert tex.count("sigma = 1.5 px") >= 5          # one row per feature table


def test_the_report_marks_the_tests_it_ran_and_those_it_did_not(report):
    _, tex = report
    line = next(l for l in tex.splitlines()
                if "test_radial_sigma_of_a_round_gaussian_is_sqrt2_sigma[sigma = 2 px]" in l)
    assert "passed" in line
    line = next(l for l in tex.splitlines()
                if "test_report.py::test_the_report_contains_every_test_name" in l)
    assert "not run" in line


def test_the_report_figures_are_written(report):
    out, tex = report
    for name in ("fig_radial_sigma.pdf", "fig_eccentricity.pdf",
                 "fig_notch.pdf"):
        assert (out / "build" / name).stat().st_size > 2000
        assert "build/" + name in tex
    assert (out / "build" / "results.xml").exists()


def test_the_report_does_not_touch_the_repository(report):
    """Everything goes to --out: a slip here once overwrote a test file."""
    out, _ = report
    assert (out / "report.tex").exists()
    with open(__file__, encoding="utf-8") as f:
        assert f.read().startswith('"""report/make_report.py')


def test_the_tex_is_well_formed(report):
    """No LaTeX is run here; this catches the usual slips: an environment
    left open, unbalanced braces, an unescaped underscore in text."""
    _, tex = report
    begins = re.findall(r"\\begin\{(\w+\*?)\}", tex)
    ends = re.findall(r"\\end\{(\w+\*?)\}", tex)
    assert sorted(begins) == sorted(ends)
    assert tex.rstrip().endswith(r"\end{document}")
    body = re.sub(r"\\path\{[^}]*\}", "", tex)       # printed as they are
    body = body.replace(r"\{", "").replace(r"\}", "")
    assert body.count("{") == body.count("}")
    for k, line in enumerate(body.splitlines(), 1):
        if line.startswith((r"\renewcommand{\UrlBreaks}", r"\includegraphics")):
            continue                                 # file names, break list
        assert line.replace(r"\$", "").count("$") % 2 == 0, (k, line)
        text = re.sub(r"\$[^$]*\$", "", line)        # outside maths
        assert not re.search(r"(?<!\\)_", text), (k, line)
        assert not re.search(r"(?<!\\)[#%]", text), (k, line)
