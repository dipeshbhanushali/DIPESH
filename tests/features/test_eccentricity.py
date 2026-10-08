"""Eccentricity of the light, from its second moments."""
import pytest

import validation as v
from dipesh import detect


@pytest.mark.parametrize("case", v.eccentricity_cases(), ids=lambda c: c.label)
def test_eccentricity_of_an_elliptical_gaussian(case):
    """e = sqrt(1 - sigma_y^2 / sigma_x^2); 0 for a round spot. Tolerance 1e-3 (0.01 absolute at e = 0)."""
    assert case.ok, case


@pytest.mark.parametrize("case", v.eccentricity_rotation_cases(), ids=lambda c: c.label)
def test_eccentricity_does_not_change_when_the_spot_is_turned_by_45_degrees(case):
    """e(rotated by 45 deg) = sqrt(1 - sigma_y^2 / sigma_x^2); tolerance 1e-3."""
    assert case.ok, case


def test_round_spots_have_low_eccentricity(frame):
    img, _ = frame(4)
    for s in detect(img, photometry=True)[0]:
        assert s.eccentricity < 0.5
        assert s.is_isolated               # planted far apart
