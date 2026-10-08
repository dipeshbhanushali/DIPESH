"""Concentration, eccentricity and profile slope describe the shape of a
spot: they must not change when the same spot is brighter."""
import pytest

import validation as v


@pytest.mark.parametrize("case", v.brightness_cases(3.0), ids=lambda c: c.label)
def test_shape_features_do_not_change_when_the_spot_is_3_times_brighter(case):
    """f(3 A) = f(A) for concentration, eccentricity, profile slope; tolerance 1e-4."""
    assert case.ok, case


@pytest.mark.parametrize("case", v.brightness_cases(0.25), ids=lambda c: c.label)
def test_shape_features_do_not_change_when_the_spot_is_4_times_fainter(case):
    """f(A / 4) = f(A) for concentration, eccentricity, profile slope; tolerance 1e-4."""
    assert case.ok, case
