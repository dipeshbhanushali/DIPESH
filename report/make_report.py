"""
Writes the test report: report/report.tex and, when pdflatex is installed,
report/report.pdf.

    py report/make_report.py              run the whole suite, write the report
    py report/make_report.py --no-pdf     stop after the .tex
    py report/make_report.py --quick      run only the fast analysis tests
                                          (the others are listed as "not run")
    py report/make_report.py --out DIR    write into DIR instead of report/

What it does:
  1. runs pytest with --junitxml=<out>/build/results.xml,
  2. computes the validation numbers of every spot feature again (true value,
     measured value, error, tolerance - tests/helpers/validation.py) and
     compares the six reference frames with tests/reference/golden.json,
  3. writes report.tex: summary, one section per algorithm with its formula,
     numbers and tests, and the list of all tests,
  4. runs pdflatex twice if it is on PATH.

It runs on demand, never as part of the test suite. Intermediate files go to
<out>/build/ (git-ignored).
"""
import argparse
import ast
import datetime
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "helpers"))
sys.path.insert(0, os.path.join(ROOT, "tests", "reference"))

GOLDEN_TOL = 1e-12            # decimals, relative; as tests/test_golden.py

QUICK_TARGETS = ["tests/features", "tests/clustering_recognition",
                 "tests/pickup"]

# Okabe-Ito: safe for colour-blind readers
BLUE, VERMILION, GREEN, ORANGE, SKY, BLACK = (
    "#0072B2", "#D55E00", "#009E73", "#E69F00", "#56B4E9", "#000000")

PACKAGES = [
    ("single_image_analysis", "Single-image analysis"),
    ("features", "Spot features"),
    ("clustering_recognition", "Clustering and recognition"),
    ("results", "Results"),
    ("pickup", "Pickup"),
    ("graphical_interface", "Graphical interface"),
    ("", "Whole program"),
]


# ════════════════════════════════════════════════════════════════════════════
# LaTeX helpers
# ════════════════════════════════════════════════════════════════════════════
_SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
            "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
            "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
            "<": r"\textless{}", ">": r"\textgreater{}", "|": r"\textbar{}"}
_UNICODE = {"σ": r"$\sigma$", "µ": r"$\mu$", "μ": r"$\mu$", "—": "---",
            "–": "--", "…": r"\ldots{}", "×": r"$\times$", "→": r"$\to$",
            "≥": r"$\ge$", "≤": r"$\le$", "²": r"$^2$", "·": r"$\cdot$",
            "Δ": r"$\Delta$", "₁": r"$_1$", "₂": r"$_2$", "÷": r"$\div$"}


def esc(text):
    """Plain text -> LaTeX. Anything it does not know becomes '?'."""
    out = []
    for ch in str(text):
        if ch in _SPECIAL:
            out.append(_SPECIAL[ch])
        elif ch in _UNICODE:
            out.append(_UNICODE[ch])
        elif ord(ch) < 128:
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)


def tex_name(name):
    r"""A test name, typeset so that it can break across lines. \path prints
    its argument as it is, so the name appears in the .tex unchanged."""
    if re.search(r"[%#{}^~\\]", name) or not name.isascii():
        return r"\texttt{" + esc(name) + "}"
    return r"\path{" + name + "}"


def num(x, digits=6):
    """A number for a table."""
    if isinstance(x, float) and math.isinf(x):
        return r"$\infty$"
    s = f"{x:.{digits}g}"
    if "e" in s:
        m, e = s.split("e")
        return rf"${m}\times10^{{{int(e)}}}$"
    return s


def sci(x):
    """A small number (an error or a tolerance) as m x 10^e; a whole number
    (a count of pixels, 0, 1) as it is."""
    if float(x).is_integer():
        return str(int(x))
    m, e = f"{x:.1e}".split("e")
    return rf"${m}\times10^{{{int(e)}}}$"


# ════════════════════════════════════════════════════════════════════════════
# Running and reading the tests
# ════════════════════════════════════════════════════════════════════════════
def pytest_env():
    return dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUTF8="1")


def collect():
    """Every test of the suite, as pytest names them (node ids)."""
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q",
                        "-p", "no:cacheprovider"], cwd=ROOT, env=pytest_env(),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return [l.strip() for l in r.stdout.splitlines()
            if "::" in l and not l.startswith(" ")]


def run_pytest(junit, targets):
    """Run the suite (or the given folders) and write the JUnit file."""
    os.makedirs(os.path.dirname(junit), exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", f"--junitxml={junit}", "-q",
           "-p", "no:cacheprovider", "-o", "junit_family=xunit1"] + targets
    r = subprocess.run(cmd, cwd=ROOT, env=pytest_env(), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    lines = [l for l in r.stdout.splitlines() if re.search(r"\d+ (passed|failed)", l)]
    return lines[-1].strip("= ") if lines else "pytest did not finish"


def read_junit(path):
    """{node id: (status, seconds, message)} from a JUnit file."""
    out = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        cls, name = case.get("classname", ""), case.get("name", "")
        node = cls.replace(".", "/") + ".py::" + name
        status, msg = "passed", ""
        for child in case:
            if child.tag in ("failure", "error"):
                status = "failed"
                msg = (child.get("message") or "").splitlines()[0][:200] \
                    if child.get("message") else ""
            elif child.tag == "skipped":
                status, msg = "skipped", child.get("message") or ""
        out[node] = (status, float(case.get("time") or 0.0), msg)
    return out


def docstrings():
    """{(file, function): first paragraph of its docstring} for every test."""
    out = {}
    for dp, dns, fns in os.walk(os.path.join(ROOT, "tests")):
        dns[:] = [d for d in dns if d not in ("__pycache__", "reference")]
        for fn in fns:
            if not (fn.startswith("test_") and fn.endswith(".py")):
                continue
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    doc = ast.get_docstring(node) or ""
                    first = doc.split("\n\n")[0]
                    out[(rel, node.name)] = " ".join(first.split())
    return out


def split_node(node):
    """'tests/features/test_x.py::test_a[b]' -> (file, function, parameter)"""
    path, _, name = node.partition("::")
    func, _, param = name.partition("[")
    return path, func, param.rstrip("]")


def package_of(node):
    parts = node.split("::")[0].split("/")
    return parts[1] if len(parts) > 2 else ""


# ════════════════════════════════════════════════════════════════════════════
# Golden comparison
# ════════════════════════════════════════════════════════════════════════════
def golden_rows():
    """Per reference frame: what the code gives now against golden.json.
    Integers must be equal; decimals are compared to GOLDEN_TOL relative, as
    in tests/test_golden.py."""
    from make_golden import measure

    with open(os.path.join(ROOT, "tests", "reference", "golden.json")) as f:
        golden = json.load(f)

    def differences(got, want):
        n = bad = last_bit = 0
        worst, fields = 0.0, set()
        pairs = [(got["info"], want["info"])] + list(zip(got["spots"], want["spots"]))
        for g, w in pairs:
            for k, v in w.items():
                n += 1
                a = g[k]
                both = isinstance(a, float) and isinstance(v, float)
                if a == v or (both and math.isnan(a) and math.isnan(v)):
                    continue
                if both and math.isfinite(a) and math.isfinite(v):
                    worst = max(worst, abs(a - v) / (abs(v) or 1.0))
                    if math.isclose(a, v, rel_tol=GOLDEN_TOL, abs_tol=1e-15):
                        last_bit += 1          # rounding, within tolerance
                        fields.add(k)
                        continue
                bad += 1
                fields.add(k)
        return n, bad, last_bit, worst, sorted(fields)

    rows = []
    for name in sorted(golden["frames"]):
        got = measure(name)
        want = golden["frames"][name]
        n, bad, last_bit, worst, fields = differences(got, want)
        rows.append({"frame": name, "count_ref": want["count"],
                     "count": got["count"], "values": n, "differ": bad,
                     "last_bit": last_bit, "worst": worst, "fields": fields})
    return rows


# ════════════════════════════════════════════════════════════════════════════
# Figures (matplotlib -> PDF)
# ════════════════════════════════════════════════════════════════════════════
def make_figures(folder):
    """Write the three figures into folder. -> {key: file name}"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    import validation as v
    from dipesh import DetectionParams
    from dipesh.features import eccentricity, radial_sigma
    from dipesh.pickup import rf_notch

    os.makedirs(folder, exist_ok=True)
    plt.rcParams.update({"font.family": "serif", "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": 0.25,
                         "pdf.fonttype": 42})
    out = {}

    # measured against true radial sigma
    sig = np.arange(1.0, 4.01, 0.25)
    true = np.sqrt(2) * sig
    wide = [radial_sigma(v.aperture(sx=s)) for s in sig]
    default = [radial_sigma(v.aperture(sx=s, params=DetectionParams(
        spot_max_radius=30))) for s in sig]
    fig, ax = plt.subplots(figsize=(3.4, 2.7))
    ax.plot(true, true, color=BLACK, lw=0.8, label="measured = true")
    ax.plot(true, wide, "o", color=BLUE, ms=4, label="aperture to 6 sigma")
    ax.plot(true, default, "s", color=VERMILION, ms=3.5, mfc="none",
            label="default plateau rule")
    ax.set_xlabel("true radial sigma, sqrt(2) sigma (px)")
    ax.set_ylabel("measured radial sigma (px)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    out["radial_sigma"] = "fig_radial_sigma.pdf"
    fig.savefig(os.path.join(folder, out["radial_sigma"]))
    plt.close(fig)

    # eccentricity against the axis ratio
    ratio = np.linspace(0.3, 1.0, 15)
    sx = 4.0
    flat = [eccentricity(v.aperture(sx=sx, sy=sx * q)) for q in ratio]
    turned = [eccentricity(v.aperture(sx=sx, sy=sx * q, angle_deg=45))
              for q in ratio]
    fine = np.linspace(0.3, 1.0, 200)
    fig, ax = plt.subplots(figsize=(3.4, 2.7))
    ax.plot(fine, np.sqrt(1 - fine ** 2), color=BLACK, lw=0.8,
            label="sqrt(1 - (sigma_y / sigma_x)^2)")
    ax.plot(ratio, flat, "o", color=BLUE, ms=4, label="measured, along x")
    ax.plot(ratio, turned, "x", color=VERMILION, ms=5, label="measured, at 45 deg")
    ax.set_xlabel("axis ratio sigma_y / sigma_x")
    ax.set_ylabel("eccentricity")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    out["eccentricity"] = "fig_eccentricity.pdf"
    fig.savefig(os.path.join(folder, out["eccentricity"]))
    plt.close(fig)

    # the pulse before and after the notch
    dt = 0.008
    t = -10 + np.arange(6000) * dt
    rng = np.random.default_rng(1)
    pulse = -0.006 * np.exp(-0.5 * ((t - 12.0) / 0.35) ** 2)
    raw = (pulse + rng.normal(0, 0.0002, len(t))
           + 0.004 * np.sin(2 * np.pi * 26.92 * t)
           + 0.0012 * np.sin(2 * np.pi * 53.84 * t))
    clean, _ = rf_notch(raw, dt, 26.92, 3, 30.0)
    keep = (t > 10.0) & (t < 14.0)
    fig, ax = plt.subplots(figsize=(5.2, 2.6))
    ax.plot(t[keep], raw[keep] * 1e3, color=SKY, lw=0.6, label="raw (trap RF on top)")
    ax.plot(t[keep], clean[keep] * 1e3, color=BLUE, lw=1.2, label="after the notch")
    ax.plot(t[keep], pulse[keep] * 1e3, color=VERMILION, lw=1.0, ls="--",
            label="the pulse put in")
    ax.set_xlabel("time (µs)")
    ax.set_ylabel("signal (mV)")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    fig.tight_layout()
    out["notch"] = "fig_notch.pdf"
    fig.savefig(os.path.join(folder, out["notch"]))
    plt.close(fig)
    return out


# ════════════════════════════════════════════════════════════════════════════
# The sections: one per algorithm
# ════════════════════════════════════════════════════════════════════════════
def sections():
    """[(title, formula in LaTeX, [test files], [(caption, cases)], figure)]"""
    import validation as v
    T = "tests/"
    return [
        ("Reading the data", "", [T + "single_image_analysis/test_loading.py"],
         [], None),
        ("Preprocessing: hot pixels, bit depth, background",
         r"A pixel is hot when $I > \mathrm{med}_{3\times3}(I) + \delta$ and "
         r"takes that median. The image is scaled by the camera bit depth, "
         r"$I \to 255\,I/F$, with $F$ the smallest of 255, 1023, 4095, 65535 "
         r"that holds the maximum. The background is "
         r"$B = (G * IM)/(G * M)$, $G$ a Gaussian blur and $M$ the mask of "
         r"pixels with $I - G * I < n\,\sigma$, "
         r"$\sigma = 1.4826\,\mathrm{MAD}$.",
         [T + "single_image_analysis/test_preprocessing.py"], [], None),
        ("Detection",
         r"With $D = \max(I - B, 0)$, a pixel is a candidate when it is the "
         r"maximum of its neighbourhood, $D > T$, $S_5 > S_{\min}$ and "
         r"$S_5/D > s_{\min}$, where $S_5$ is the $5\times5$ sum and "
         r"$T = \max(T_{\mathrm{abs}},\, n\,\sigma)$. Candidates are taken "
         r"brightest first; each removes the others within $d_{\min}$.",
         [T + "single_image_analysis/test_detection.py"], [], None),
        ("Aperture",
         r"$L(r) = \sum_{\rho \le r} (D - b)$ is summed in growing discs. The "
         r"aperture stops at the first $r$ with "
         r"$L(r) - L(r-1) < f\,L(r-1)$ ($f$ = plateau\_frac $= 0.02$), or at "
         r"spot\_max\_radius.",
         [T + "features/test_aperture.py"],
         [("Radius used, against the rule applied to a continuous Gaussian "
           "(absolute error, px).", v.aperture_radius_cases)], None),
        ("Luminosity",
         r"$L = \sum_{\rho \le R} (D - b)$. For a Gaussian spot of amplitude "
         r"$A$ and width $\sigma$: $L = 2\pi A \sigma^2\,(1 - e^{-R^2/2\sigma^2})$.",
         [T + "features/test_luminosity.py"],
         [("Aperture out to $6\\sigma$.", v.luminosity_cases),
          ("Default plateau rule.", v.plateau_luminosity_cases),
          ("Through detect() with the default settings.",
           v.pipeline_luminosity_cases)], None),
        ("Area", r"$N = \#\{\text{pixels with } \rho^2 \le R^2\}$.",
         [T + "features/test_area.py"],
         [("Pixels in the aperture.", v.area_cases)], None),
        ("Radial sigma",
         r"With $w = \max(D - b, 0)$ and $r$ the distance from the centroid "
         r"$\sum w\,\mathbf{x} / \sum w$: "
         r"$\sigma_r = \sqrt{\sum w\,r^2 / \sum w}$. For a round Gaussian "
         r"$\sigma_r = \sqrt{2}\,\sigma$.",
         [T + "features/test_radial_sigma.py"],
         [("Aperture out to $6\\sigma$.", v.radial_sigma_cases)],
         "radial_sigma"),
        ("Concentration",
         r"$C = \sum_{r \le 2\,\mathrm{px}} w / \sum w$. For a continuous "
         r"Gaussian $C = 1 - e^{-4/(2\sigma^2)}$.",
         [T + "features/test_concentration.py"],
         [("Against the continuous formula (spot centred 0.3, 0.2 px off a "
           "pixel).", v.concentration_cases),
          ("Against the sum over the same pixels.", v.concentration_pixel_cases),
          ("Spot centred exactly on a pixel: four pixels lie at exactly "
           "$r = 2$ and rounding decides which count.",
           v.concentration_on_pixel_cases)], None),
        ("Eccentricity",
         r"From the second moments of $w$ about the centroid, with "
         r"eigenvalues $\lambda_1 \ge \lambda_2$: "
         r"$e = \sqrt{1 - \lambda_2/\lambda_1}$. For an elliptical Gaussian "
         r"$e = \sqrt{1 - \sigma_y^2/\sigma_x^2}$.",
         [T + "features/test_eccentricity.py"],
         [("Along the pixel axes.", v.eccentricity_cases),
          ("Turned by 45 degrees.", v.eccentricity_rotation_cases)],
         "eccentricity"),
        ("Profile slope",
         r"The slope of the straight line fitted to $\ln w$ against $r$ over "
         r"the aperture pixels with $w > 0$.",
         [T + "features/test_profile_slope.py"], [], None),
        ("Isolation",
         r"$d_i = \min_{j \ne i} |\mathbf{p}_i - \mathbf{p}_j|$; a spot is "
         r"isolated when $d_i > f_{\mathrm{iso}}\,R_i$.",
         [T + "features/test_isolation.py"], [], None),
        ("Brightness independence",
         r"Concentration, eccentricity and profile slope are ratios of sums "
         r"of $w$: $f(kA) = f(A)$.",
         [T + "features/test_brightness_independence.py"],
         [("The same spot, three times brighter.", v.brightness_cases)], None),
        ("Image luminosity and the count from light",
         r"$L_{\mathrm{int}} = \sum_{\mathrm{MCP}} D - \bar b\,N_{\mathrm{MCP}}$, "
         r"$\bar b$ the mean of the spot-free pixels; "
         r"$N_{\mathrm{lum}} = L_{\mathrm{int}} / \langle L_{\mathrm{ap}} \rangle$, "
         r"the mean light in a fixed aperture on the counted spots.",
         [T + "single_image_analysis/test_image_luminosity.py"], [], None),
        ("Separation score and best cut",
         r"$s = |\mu_a - \mu_b| / (\sigma_a + \sigma_b)$. The best cut $t$ "
         r"minimises $\frac{1}{2}[P(a > t) + P(b \le t)]$.",
         [T + "clustering_recognition/test_separation.py"], [], None),
        ("Principal components",
         r"Columns standardised to $Z$, then $Z = U S V^{T}$: scores $US$, "
         r"explained variance $S_k^2/\sum S^2$, loadings $V^{T}$. The ellipse "
         r"is the $n\sigma$ contour of the covariance of two scores.",
         [T + "clustering_recognition/test_pca.py"], [], None),
        ("Run results", "", [T + "results/test_run.py"], [], None),
        ("Averages and fits",
         r"Repeats at the same $x$: mean and $s/\sqrt{n}$ (or $s$). Fits: "
         r"$ax + b$, $ax^2 + bx + c$, $a\,e^{bx} + c$, with "
         r"$R^2 = 1 - \sum (y - \hat y)^2 / \sum (y - \bar y)^2$.",
         [T + "results/test_trends.py"], [], None),
        ("Export and master archive", "", [T + "results/test_export.py"],
         [], None),
        ("Pickup: RF notch",
         r"An IIR notch at $k f_0$ ($f_0 = 26.92$ MHz, $k = 1, 2, \dots$ "
         r"below the Nyquist frequency), run forwards and backwards so the "
         r"phase is zero and the pulse stays where it is.",
         [T + "pickup/test_rf_filter.py"], [], "notch"),
        ("Pickup: the pulse",
         r"Baseline: median of the first 10\,\% of the trace; noise "
         r"$1.4826\,\mathrm{MAD}$ there. The pulse is found when "
         r"peak/noise $\ge n_\sigma$. Width: full width at half maximum. "
         r"Area: $\sum (v - \mathrm{baseline})\,\Delta t$ while above "
         r"$3\times$ noise.",
         [T + "pickup/test_pulse.py", T + "pickup/test_measure.py"], [], None),
        ("Graphical interface", "",
         [T + "graphical_interface/test_window.py",
          T + "graphical_interface/test_top_bar.py",
          T + "graphical_interface/test_combo_boxes.py",
          T + "graphical_interface/test_datasets.py",
          T + "graphical_interface/test_live_detection.py",
          T + "graphical_interface/test_run_all_export.py",
          T + "graphical_interface/test_pickup_page.py",
          T + "graphical_interface/test_threads.py"], [], None),
        ("Whole program", "",
         [T + "test_golden.py", T + "test_public_api.py", T + "test_about.py",
          T + "test_report.py"], [], None),
    ]


CAPTIONS = {"radial_sigma": "Measured against true radial sigma, round "
                            "Gaussian spots.",
            "eccentricity": "Eccentricity against the axis ratio, "
                            "$\\sigma_x = 4$ px.",
            "notch": "A 6 mV pulse under 4 mV of trap RF, before and after "
                     "the notch."}


# ════════════════════════════════════════════════════════════════════════════
# Writing the .tex
# ════════════════════════════════════════════════════════════════════════════
STATUS_TEX = {"passed": "passed", "failed": r"\textbf{FAILED}",
              "skipped": "skipped", "not run": "not run"}


def case_table(caption, cases):
    absolute = any(c.absolute or not c.true for c in cases)
    head = "absolute error" if absolute else "relative error"
    lines = [r"\begin{center}", r"\begin{tabular}{lrrrrl}", r"\toprule",
             rf"case & true & measured & {head} & tolerance & \\", r"\midrule"]
    for c in cases:
        lines.append(f"{esc(c.label)} & {num(c.true)} & {num(c.measured)} & "
                     f"{sci(c.error)} & {sci(c.tol)} & "
                     f"{'ok' if c.ok else STATUS_TEX['failed']} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{center}",
              r"\noindent{\small " + caption + r"}", ""]
    return lines


def git_commit():
    def git(*a):
        try:
            return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                                  text=True).stdout.strip()
        except OSError:
            return ""
    head = git("rev-parse", "--short", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{4,40}", head):
        return ""                                 # not a repository (yet)
    changed = [l for l in git("status", "--porcelain").splitlines()
               if not l[3:].startswith("report/")]
    return head + (" (with uncommitted changes)" if changed else "")


def versions():
    import cv2
    import matplotlib
    import numpy
    import scipy
    out = [("Python", platform.python_version()), ("numpy", numpy.__version__),
           ("OpenCV", cv2.__version__), ("scipy", scipy.__version__),
           ("matplotlib", matplotlib.__version__)]
    try:
        import PySide6
        import pyqtgraph
        out += [("PySide6", PySide6.__version__),
                ("pyqtgraph", pyqtgraph.__version__)]
    except ImportError:
        pass
    return out


def write_tex(path, results, all_nodes, summary, golden, figs, quick):
    from dipesh import _about
    docs = docstrings()

    def status(node):
        return results.get(node, ("not run", 0.0, ""))[0]

    counts = {}
    for node in all_nodes:
        c = counts.setdefault(package_of(node), {"passed": 0, "failed": 0,
                                                 "skipped": 0, "not run": 0})
        c[status(node)] += 1
    total = {k: sum(c[k] for c in counts.values())
             for k in ("passed", "failed", "skipped", "not run")}

    L = []
    add = L.append
    add(r"""\documentclass[10pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{mathpazo}
\usepackage[margin=24mm]{geometry}
\usepackage{amsmath}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{graphicx}
\usepackage[obeyspaces]{url}
\renewcommand{\UrlBreaks}{\do\_\do\/\do\[\do\]\do\.\do\-\do\,}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\begin{document}
""")
    add(r"\begin{center}")
    add(r"{\LARGE " + esc(_about.NAME) + r" --- test report}\\[6pt]")
    add(esc(_about.TITLE) + r"\\[4pt]")
    commit = git_commit()
    add(f"version {esc(_about.VERSION)}"
        + (f", commit {esc(commit)}" if commit else "") + "\\\\")
    add(f"report written {datetime.date.today().isoformat()}")
    add(r"\end{center}")
    add("")

    # ── summary ────────────────────────────────────────────────────────────
    add(r"\section{Summary}")
    add(f"{len(all_nodes)} tests: {total['passed']} passed, "
        f"{total['failed']} failed, {total['skipped']} skipped"
        + (f", {total['not run']} not run" if total["not run"] else "") + ". "
        + "pytest reported: " + esc(summary) + ".")
    if quick:
        add(r"\textbf{Quick run:} only the fast analysis tests were run "
            r"(" + esc(", ".join(QUICK_TARGETS)) + r"); the others are listed "
            r"as not run.")
    add(r"\begin{center}")
    add(r"\begin{tabular}{lrrrrr}")
    add(r"\toprule")
    add(r"package & tests & passed & failed & skipped & not run \\")
    add(r"\midrule")
    for key, title in PACKAGES:
        c = counts.get(key)
        if not c:
            continue
        add(f"{esc(title)} & {sum(c.values())} & {c['passed']} & {c['failed']}"
            f" & {c['skipped']} & {c['not run']} \\\\")
    add(r"\midrule")
    add(f"all & {len(all_nodes)} & {total['passed']} & {total['failed']} & "
        f"{total['skipped']} & {total['not run']} \\\\")
    add(r"\bottomrule")
    add(r"\end{tabular}")
    add(r"\end{center}")
    add("Software: " + ", ".join(f"{esc(n)} {esc(v)}" for n, v in versions())
        + f"; {esc(platform.system())} {esc(platform.release())}, "
        + esc(platform.processor() or platform.machine()) + ".")
    add("")

    # ── golden ─────────────────────────────────────────────────────────────
    add(r"\section{The six reference frames}")
    add(r"Every count, every per-spot value and every per-image value of the "
        r"six reference frames (synthetic, written by "
        r"\path{tests/reference/make_frames.py}) is compared with "
        r"\path{tests/reference/golden.json}. Counts, integers and booleans "
        r"must be equal; decimal values must agree to $10^{-12}$ relative.")
    add(r"\begin{center}")
    add(r"\begin{tabular}{lrrrrrrl}")
    add(r"\toprule")
    add(r"frame & \multicolumn{2}{c}{count} & values & outside & last-bit & "
        r"largest rel.\ diff. & field \\")
    add(r" & ref. & now & & tolerance & only & & \\")
    add(r"\midrule")
    for k, r in enumerate(golden, 1):
        outside = str(r["differ"]) if not r["differ"] else \
            r"\textbf{" + str(r["differ"]) + "}"
        add(f"{k} & {r['count_ref']} & {r['count']} & {r['values']} & "
            f"{outside} & {r['last_bit']} & {sci(r['worst'])} & "
            f"{esc(', '.join(r['fields']) or '-')} \\\\")
    add(r"\bottomrule")
    add(r"\end{tabular}")
    add(r"\end{center}")
    add(r"{\small Frames: " + "; ".join(
        f"{k} = " + tex_name(r["frame"]) for k, r in enumerate(golden, 1))
        + ".}")
    add("")
    if any(r["differ"] for r in golden):
        add(r"\textbf{Note.} Some values are outside the tolerance. This is a "
            r"change of the physics and must be looked at.")
    elif any(r["last_bit"] for r in golden):
        add(r"The values counted as last-bit differ from the reference by a "
            r"relative amount of order $10^{-15}$. They come from a "
            r"least-squares fit done by BLAS/LAPACK, whose rounding depends on "
            r"the processor.")
    add("")

    # ── one section per algorithm ──────────────────────────────────────────
    by_file = {}
    for node in all_nodes:
        test_file, func, _ = split_node(node)
        by_file.setdefault(test_file, {}).setdefault(func, []).append(node)

    listed = set()
    for title, formula, files, tables, figure in sections():
        funcs = [(f, fn, nodes) for f in files
                 for fn, nodes in by_file.get(f, {}).items()]
        if not funcs:
            continue
        listed.update(files)
        add(r"\section{" + esc(title) + "}")
        if formula:
            add(formula)
            add("")
        for caption, cases in tables:
            L.extend(case_table(caption, cases()))
        if title == "Profile slope":
            import validation as v
            add(r"\begin{center}")
            add(r"\begin{tabular}{rr}")
            add(r"\toprule")
            add(r"$\sigma$ (px) & profile slope (1/px) \\")
            add(r"\midrule")
            for s, slope in v.profile_slope_values():
                add(f"{num(s)} & {num(slope, 4)} \\\\")
            add(r"\bottomrule")
            add(r"\end{tabular}")
            add(r"\end{center}")
        if figure and figure in figs:
            add(r"\begin{center}")
            add(r"\includegraphics{build/" + figs[figure] + "}\\\\")
            add(r"{\small " + CAPTIONS[figure] + "}")
            add(r"\end{center}")
        add(r"\begin{longtable}{@{}p{0.86\textwidth}r@{}}")
        add(r"\toprule")
        add(r"test & result \\")
        add(r"\midrule")
        add(r"\endhead")
        for f, fn, nodes in funcs:
            st = [status(n) for n in nodes]
            if "failed" in st:
                res = STATUS_TEX["failed"]
            elif all(s == "passed" for s in st):
                res = "passed"
            elif all(s == "not run" for s in st):
                res = "not run"
            else:
                res = "skipped" if "skipped" in st else "partly run"
            if len(nodes) > 1:
                res += f" ({st.count('passed')}/{len(nodes)})"
            words = esc(fn[len("test_"):].replace("_", " "))
            doc = docs.get((f, fn), "")
            cell = words + (r"\newline{\small\itshape " + esc(doc) + "}"
                            if doc else "")
            add(f"{cell} & {res} \\\\")
        add(r"\bottomrule")
        add(r"\end{longtable}")
        add("")

    # ── every test ─────────────────────────────────────────────────────────
    add(r"\section{All tests}")
    add("Every test by package, as pytest names it, with its result and the "
        "time it took.")
    for key, title in PACKAGES:
        nodes = [n for n in all_nodes if package_of(n) == key]
        if not nodes:
            continue
        add(r"\subsection*{" + esc(title) + "}")
        add(r"\begin{longtable}{@{}p{0.76\textwidth}lr@{}}")
        add(r"\toprule")
        add(r"test & result & time (s) \\")
        add(r"\midrule")
        add(r"\endhead")
        for n in nodes:
            st, secs, msg = results.get(n, ("not run", 0.0, ""))
            add(f"{tex_name(n)} & {STATUS_TEX[st]} & "
                f"{secs:.2f} \\\\" if st != "not run" else
                f"{tex_name(n)} & {STATUS_TEX[st]} & \\\\")
            if st == "failed" and msg:
                add(r"\multicolumn{3}{@{}p{0.95\textwidth}@{}}{\small\quad "
                    + esc(msg) + r"} \\")
        add(r"\bottomrule")
        add(r"\end{longtable}")
    add(r"\end{document}")

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


# ════════════════════════════════════════════════════════════════════════════
def pdflatex(tex):
    """Run pdflatex twice. -> True when the PDF was written."""
    exe = shutil.which("pdflatex")
    if not exe:
        print("pdflatex is not on PATH: the PDF was not built. The .tex is in "
              f"{tex}; install TeX Live or MiKTeX and run this again.")
        return False
    folder = os.path.dirname(tex)
    for _ in range(2):
        r = subprocess.run([exe, "-interaction=nonstopmode", "-halt-on-error",
                            "-output-directory", os.path.join(folder, "build"),
                            os.path.basename(tex)], cwd=folder,
                           capture_output=True, text=True, errors="replace")
        if r.returncode != 0:
            print("pdflatex failed:\n" + "\n".join(r.stdout.splitlines()[-25:]))
            return False
    built = os.path.join(folder, "build", "report.pdf")
    shutil.copyfile(built, os.path.join(folder, "report.pdf"))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-pdf", action="store_true",
                    help="write the .tex only")
    ap.add_argument("--quick", action="store_true",
                    help="run only the fast analysis tests")
    ap.add_argument("--out", default=HERE, help="folder for report.tex")
    args = ap.parse_args(argv)

    out = os.path.abspath(args.out)
    build = os.path.join(out, "build")
    os.makedirs(build, exist_ok=True)
    junit = os.path.join(build, "results.xml")

    print("collecting the tests...")
    all_nodes = collect()
    print(f"running {'the fast tests' if args.quick else 'the whole suite'}...")
    summary = run_pytest(junit, QUICK_TARGETS if args.quick else [])
    print("  " + summary)
    results = read_junit(junit)
    for node in results:                      # anything collect() missed
        if node not in all_nodes:
            all_nodes.append(node)

    print("validation numbers, golden comparison, figures...")
    golden = golden_rows()
    figs = make_figures(build)
    tex = os.path.join(out, "report.tex")
    write_tex(tex, results, all_nodes, summary, golden, figs, args.quick)
    print("wrote", tex)
    if not args.no_pdf and pdflatex(tex):
        print("wrote", os.path.join(out, "report.pdf"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
