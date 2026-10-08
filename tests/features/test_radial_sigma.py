"""Radial sigma: the RMS radius of the light."""
import pytest

import validation as v
from dipesh.features import radial_sigma


@pytest.mark.parametrize("case", v.radial_sigma_cases(), ids=lambda c: c.label)
def test_radial_sigma_of_a_round_gaussian_is_sqrt2_sigma(case):
    """sqrt(<r^2>) = sqrt(2) sigma in 2-D. Aperture out to 6 sigma; tolerance 1e-3."""
    assert case.ok, case


@pytest.mark.parametrize("sigma", v.SIGMAS)
def test_radial_sigma_does_not_depend_on_the_brightness(sigma):
    """radial_sigma(k A) = radial_sigma(A); tolerance 1e-5."""
    a = radial_sigma(v.aperture(amp=50.0, sx=sigma))
    b = radial_sigma(v.aperture(amp=150.0, sx=sigma))
    assert b == pytest.approx(a, rel=1e-5)


@pytest.mark.parametrize("sigma", v.SIGMAS)
def test_the_default_aperture_cuts_radial_sigma_by_at_most_5_percent(sigma):
    """With the plateau rule (R = 3.3 to 4 sigma): 0.95 sqrt(2) sigma < sqrt(<r^2>) < sqrt(2) sigma."""
    from dipesh import DetectionParams
    got = radial_sigma(v.aperture(sx=sigma, params=DetectionParams(
        spot_max_radius=30)))
    assert 0.95 * 2 ** 0.5 * sigma < got < 2 ** 0.5 * sigma
