"""The names scripts import from dipesh keep working, and the
analysis never pulls in Qt."""
import os
import re
import subprocess
import sys

PACKAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                       "dipesh")

PUBLIC = """scan analyse DetectionParams detect load_image to_float
measure_pickup separation_score best_threshold pca average_xy fit_curve
write_outputs append_master PickupConfig ScopeConfig RunResult Spot
DetectionInfo Item RUN_METRICS DEFAULT_PARAMS SPOT_FEATURES find_run_folders
find_tiff parse_batman prepare __version__""".split()


def test_every_public_name_is_importable_from_the_package():
    import dipesh
    missing = [n for n in PUBLIC if not hasattr(dipesh, n)]
    assert not missing, missing
    assert callable(dipesh.pca)             # the function,
    assert callable(dipesh.measure_pickup)  # not the module


def test_importing_the_analysis_does_not_import_qt():
    code = ("import sys, dipesh, dipesh.features, "
            "dipesh.results, dipesh.pickup, "
            "dipesh.clustering_recognition; "
            "bad = [m for m in sys.modules if m.split('.')[0] in "
            "('PySide6', 'pyqtgraph', 'shiboken6')]; "
            "sys.exit(1 if bad else 0)")
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_no_file_outside_graphical_interface_imports_qt():
    """Qt (PySide6, pyqtgraph, shiboken6) is imported only under
    dipesh/graphical_interface/: read every other .py file of the package."""
    qt = re.compile(r"^\s*(import|from)\s+(PySide6|pyqtgraph|shiboken6)\b",
                    re.M)
    gui = os.path.normpath(os.path.join(PACKAGE, "graphical_interface"))
    bad = []
    for folder, dirs, files in os.walk(PACKAGE):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if os.path.normpath(folder).startswith(gui):
            continue
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(folder, f)
                with open(path, encoding="utf-8") as fh:
                    if qt.search(fh.read()):
                        bad.append(os.path.relpath(path, PACKAGE))
    assert not bad, bad
