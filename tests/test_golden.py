"""
Regression guard: every count, every per-spot number and every per-image number
on the six reference frames must equal tests/reference/golden.json: counts and
integers exactly, decimal values to 1e-12 relative. If this test fails, the
code changed the physics - fix the code, never the reference.
"""
import json
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "reference")
sys.path.insert(0, REF)
from make_golden import measure                                    # noqa: E402

with open(os.path.join(REF, "golden.json")) as f:
    GOLDEN = json.load(f)


def same(a, b):
    """Counts, integers, booleans and lists of them must be equal exactly.
    Decimal values must agree to 1e-12 relative (NaN equals NaN): the last
    bit of BLAS, which np.polyfit goes through for profile_slope, depends on
    the CPU, so the same code gives a different last bit on another machine.
    A real change of the arithmetic shows far above 1e-12."""
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-15)
    return a == b


@pytest.mark.parametrize("name", sorted(GOLDEN["frames"]))
def test_reference_frame_matches_golden(name):
    want, got = GOLDEN["frames"][name], measure(name)
    assert got["count"] == want["count"], f"count {got['count']} != {want['count']}"
    for k, v in want["info"].items():
        assert same(got["info"][k], v), f"info.{k}: {got['info'][k]!r} != {v!r}"
    for i, (gs, ws) in enumerate(zip(got["spots"], want["spots"])):
        for k, v in ws.items():
            assert same(gs[k], v), f"spot {i} {k}: {gs[k]!r} != {v!r}"


def test_default_params_unchanged():
    from dataclasses import asdict
    from dipesh import DetectionParams
    assert json.loads(json.dumps(asdict(DetectionParams()))) == GOLDEN["params"]
