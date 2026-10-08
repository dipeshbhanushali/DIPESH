"""Finding and measuring the extraction pulse."""
import math

import numpy as np
import pytest

from dipesh.pickup import analyse_pulse

T = np.arange(4000) * 0.008


def gauss(amp, t0=16.0, width=0.35):
    return amp * np.exp(-0.5 * ((T - t0) / width) ** 2)


def test_a_flat_trace_has_no_pulse():
    t = np.arange(2000) * 0.01
    assert not analyse_pulse(t, np.random.default_rng(0).normal(0, 1e-3, 2000))["found"]


@pytest.mark.parametrize("sign", [1, -1])
def test_a_gaussian_pulse_is_measured(sign):
    """Amplitude A, time t0, FWHM = 2 sqrt(2 ln 2) w, area = A w sqrt(2 pi)."""
    A, w = 0.02, 0.35
    p = analyse_pulse(T, 0.003 + sign * gauss(A, 16.0, w))
    assert p["found"] and p["polarity"] == sign
    assert p["baseline"] == pytest.approx(0.003, abs=1e-6)
    assert p["peak_time_us"] == pytest.approx(16.0, abs=0.008)
    assert p["amplitude_V"] == pytest.approx(A, rel=1e-3)
    # the half-maximum crossings are whole samples: one sample each side
    assert p["width_us"] == pytest.approx(2 * math.sqrt(2 * math.log(2)) * w,
                                          abs=2 * 0.008)
    # integrated down to 3 sigma of the noise floor (1e-4 V): 99.9 % of it
    assert p["area"] == pytest.approx(A * w * math.sqrt(2 * math.pi), rel=0.01)


def test_the_significance_is_the_peak_over_the_baseline_noise():
    """n_sigma = peak / (1.4826 MAD of the first 10 % of the trace)."""
    rng = np.random.default_rng(4)
    v = rng.normal(0, 1e-3, len(T)) + gauss(0.02)
    p = analyse_pulse(T, v)
    assert p["noise"] == pytest.approx(1e-3, rel=0.15)
    assert p["n_sigma"] == pytest.approx(p["amplitude_V"] / p["noise"])


def test_a_pulse_below_the_threshold_is_not_found():
    rng = np.random.default_rng(4)
    v = rng.normal(0, 1e-3, len(T)) + gauss(0.008)
    assert analyse_pulse(T, v, nsigma=5.0)["found"]
    p = analyse_pulse(T, v, nsigma=20.0)
    assert not p["found"] and p["peak_time_us"] is None and p["area"] == 0.0
