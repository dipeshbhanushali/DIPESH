"""
Shared fixtures. The builders live in tests/helpers/synthetic.py; a test asks
for one by name and calls it:

    def test_x(frame):
        img, pts = frame(7)
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "helpers"))

import synthetic                                                   # noqa: E402


@pytest.fixture
def frame():
    """frame(n, size, amp, seed, hot, sigma) -> (image, [(x, y)])"""
    return synthetic.frame


@pytest.fixture
def run_folder():
    """run_folder(root, run_number, n, batman, ...) -> (folder, [(x, y)])"""
    return synthetic.run_folder


@pytest.fixture
def picoscope():
    """picoscope(folder, tag, amp, t_pulse, rf) writes four channel files."""
    return synthetic.picoscope


@pytest.fixture
def gaussian_spot():
    """gaussian_spot(amp, sx, sy, angle_deg, size, centre, offset)
    -> (noise-free image, (cx, cy))"""
    return synthetic.gaussian_spot
