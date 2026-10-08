"""Profile slope: log of the light against the distance from the centroid."""
import pytest

import validation as v
from dipesh import DetectionParams, Spot
from dipesh.features import profile_slope


def test_profile_slope_is_negative():
    """The light falls with distance: slope < 0."""
    assert all(slope < 0 for _, slope in v.profile_slope_values())


def test_profile_slope_is_steeper_for_a_narrower_spot():
    """slope(sigma) increases towards 0 with sigma: more negative for a smaller sigma."""
    slopes = [slope for _, slope in v.profile_slope_values()]
    assert slopes == sorted(slopes)


def test_profile_slope_of_an_exponential_spot_is_minus_one_over_its_length():
    """w = A exp(-r / L)  ->  log w = log A - r / L, slope = -1 / L; tolerance 1e-3."""
    import numpy as np
    from dipesh.features import grow
    L = 2.5
    yy, xx = np.mgrid[0:65, 0:65].astype(float)
    img = (100.0 * np.exp(-np.hypot(xx - 32, yy - 32) / L)).astype(np.float32)
    ap = grow(img, 32, 32, 0.0, DetectionParams(plateau_frac=0.0,
                                                 spot_max_radius=10))
    assert profile_slope(ap) == pytest.approx(-1 / L, rel=1e-3)


def test_fewer_than_three_lit_pixels_give_a_slope_of_zero():
    import numpy as np
    from dipesh.features import measure_spots
    img = np.zeros((33, 33), np.float32)
    img[16, 16] = 50.0
    s = Spot(16, 16, 50.0, 50.0)
    measure_spots(img, [s], 0.0, DetectionParams())
    assert s.profile_slope == 0.0
