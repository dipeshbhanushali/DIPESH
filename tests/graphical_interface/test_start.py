"""The program starts the way a user starts it and closes cleanly."""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_python_m_dipesh_starts_the_app_and_selftest_closes_it():
    """py -m dipesh --selftest=1: the window opens, closes after
    1 s, exit code 0, nothing on stderr about threads."""
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    r = subprocess.run([sys.executable, "-m", "dipesh",
                        "--selftest=1"], cwd=ROOT, env=env, timeout=120,
                       capture_output=True, text=True, errors="replace")
    assert r.returncode == 0, r.stderr
    assert "Traceback" not in r.stderr
    assert "different thread" not in r.stderr


def test_the_dipesh_entry_point_is_the_same_main():
    from importlib.metadata import entry_points
    eps = [e for e in entry_points(group="gui_scripts") if e.name == "dipesh"]
    assert eps, "dipesh is not installed: py -m pip install -e \".[dev]\""
    assert eps[0].value == "dipesh.graphical_interface.app:main"
    from dipesh.graphical_interface.app import main
    assert eps[0].load() is main
