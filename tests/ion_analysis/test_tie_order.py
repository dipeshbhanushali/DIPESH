"""The order of equally bright candidates (tie_order.py): reading order, and
NumPy 1.x's argsort, checked against what NumPy 1.26 itself gave on arrays
full of ties (recorded in numpy1_argsort.json)."""
import json
import os

import numpy as np

from dipesh.ion_analysis.tie_order import numpy1, numpy1_argsort, reading

with open(os.path.join(os.path.dirname(__file__), "numpy1_argsort.json")) as f:
    RECORDED = json.load(f)


def test_the_port_gives_numpy_1_26s_argsort():
    assert RECORDED["made_with"].startswith("numpy 1.")
    for a in RECORDED["arrays"]:
        assert numpy1_argsort(a["values"]) == a["numpy_1_26_argsort"], \
            len(a["values"])


def test_numpy1_is_brightest_first():
    v = np.array([3, 9, 1, 9, 5], np.float32)
    order = numpy1(v)
    assert list(v[order]) == sorted(v, reverse=True)


def test_reading_order_is_brightest_first_then_row_by_row():
    v = np.array([5, 9, 5, 9, 1], np.float32)
    assert list(reading(v)) == [1, 3, 0, 2, 4]
