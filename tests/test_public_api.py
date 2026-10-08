"""The names scripts import from dipesh keep working, and the
analysis never pulls in Qt."""
import subprocess
import sys

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
