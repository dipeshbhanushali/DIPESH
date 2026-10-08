"""Luminosity: the light in the aperture.

Noise-free Gaussian spots, see tests/helpers/validation.py for how they are
made and why the tolerances are what they are.
"""
import numpy as np
import pytest

import validation as v
from dipesh import detect
from dipesh.features import luminosity


@pytest.mark.parametrize("case", v.luminosity_cases(), ids=lambda c: c.label)
def test_luminosity_of_a_gaussian_is_2_pi_A_sigma_squared(case):
    """L = 2 pi A sigma^2. Aperture out to 6 sigma; tolerance 1e-4 (float32)."""
    assert case.ok, case


@pytest.mark.parametrize("case", v.plateau_luminosity_cases(), ids=lambda c: c.label)
def test_the_plateau_rule_keeps_the_luminosity_within_3_percent(case):
    """L(R) = 2 pi A sigma^2 (1 - exp(-R^2 / 2 sigma^2)), R from the 2 % rule; tolerance 3 %."""
    assert case.ok, case
    assert case.measured < case.true                 # the tail is cut, never added


@pytest.mark.parametrize("sigma", v.SIGMAS)
def test_doubling_the_amplitude_doubles_the_luminosity(sigma):
    """L(2A) = 2 L(A); tolerance 1e-6 (the factor 2 is exact in float32)."""
    one = luminosity(v.aperture(amp=60.0, sx=sigma))
    two = luminosity(v.aperture(amp=120.0, sx=sigma))
    assert two == pytest.approx(2 * one, rel=1e-6)


@pytest.mark.parametrize("case", v.pipeline_luminosity_cases(), ids=lambda c: c.label)
def test_luminosity_through_the_whole_pipeline_is_within_7_percent(case):
    """detect() with default settings: L = 2 pi A sigma^2 within 7 %."""
    assert case.ok, case


@pytest.mark.parametrize("sigma", v.SIGMAS)
def test_a_flat_offset_does_not_change_the_luminosity(sigma):
    """L(image + c) = L(image): the background step removes c. Tolerance 1e-3."""
    a = v.pipeline_spot(sigma, offset=10.0).luminosity
    b = v.pipeline_spot(sigma, offset=40.0).luminosity
    assert b == pytest.approx(a, rel=1e-3)


def test_photometry_measures_brighter_spots_as_brighter(frame):
    dim, _ = frame(4, amp=150)
    bright, _ = frame(4, amp=240)
    ld = np.mean([s.luminosity for s in detect(dim, photometry=True)[0]])
    lb = np.mean([s.luminosity for s in detect(bright, photometry=True)[0]])
    assert lb > ld > 0
