"""Averaging repeats and fitting curves."""
import math

import numpy as np
import pytest

from dipesh import average_xy, fit_curve


def test_averaging_groups_repeats():
    x, y, e, n = average_xy([1, 1, 2, 2, 2], [10, 12, 5, 5, 8])
    assert list(x) == [1, 2] and list(n) == [2, 3]
    assert y[0] == 11 and abs(y[1] - 6) < 1e-9 and e[0] > 0


def test_the_error_is_the_standard_error_or_the_standard_deviation():
    """sem = std(ddof=1) / sqrt(n); [10, 12, 14] -> std 2, sem 2 / sqrt(3)."""
    xs, ys = [1, 1, 1], [10, 12, 14]
    assert average_xy(xs, ys, error="std")[2][0] == pytest.approx(2.0)
    assert average_xy(xs, ys, error="sem")[2][0] == pytest.approx(2 / math.sqrt(3))


def test_a_single_run_has_no_error_bar():
    x, y, e, n = average_xy([3], [7])
    assert list(y) == [7] and list(e) == [0] and list(n) == [1]


def test_averaging_drops_non_finite_points_and_sorts_by_x():
    x, y, e, n = average_xy([2, 1, float("nan"), 1], [4, 1, 9, float("inf")])
    assert list(x) == [1, 2] and list(y) == [1, 4]
    assert all(len(v) == 0 for v in average_xy([], []))


def test_bin_width_groups_nearby_x_and_min_n_drops_thin_groups():
    x, y, e, n = average_xy([0.9, 1.1, 2.0], [10, 20, 5], bin_width=1.0)
    assert list(n) == [2, 1] and y[0] == 15 and x[0] == pytest.approx(1.0)
    assert list(average_xy([0.9, 1.1, 2.0], [10, 20, 5], bin_width=1.0,
                           min_n=2)[3]) == [2]


def test_quadratic_fit_recovers_its_coefficients():
    x = np.linspace(0, 10, 30)
    res = fit_curve(x, 0.5 * x ** 2 - 2 * x + 3, kind="quadratic")
    assert np.allclose(res["params"], [0.5, -2, 3], atol=1e-6)
    assert res["r2"] > 0.999999
    assert fit_curve([1, 2], [1, 2], kind="linear") is None


def test_linear_fit_recovers_slope_and_offset():
    """y = 3 x - 1 -> a = 3, b = -1, R^2 = 1."""
    x = np.arange(8.0)
    res = fit_curve(x, 3 * x - 1, kind="linear")
    assert np.allclose(res["params"], [3, -1], atol=1e-8) and res["r2"] > 0.999999


def test_exponential_fit_recovers_its_coefficients():
    """y = 40 exp(-0.5 x) + 5."""
    x = np.linspace(0, 10, 40)
    res = fit_curve(x, 40 * np.exp(-0.5 * x) + 5, kind="exponential")
    assert np.allclose(res["params"], [40, -0.5, 5], rtol=1e-4)


def test_a_weighted_fit_follows_the_precise_points():
    """Two lines mixed: the points with small errors decide the fit."""
    x = np.array([0, 1, 2, 3, 0, 1, 2, 3], float)
    y = np.r_[2 * x[:4], 5 * x[4:] + 1]
    err = np.r_[np.full(4, 1e-3), np.full(4, 1e3)]
    res = fit_curve(x, y, err, kind="linear")
    assert np.allclose(res["params"], [2, 0], atol=1e-3)
    plain = fit_curve(x, y, err, kind="linear", weighted=False)
    assert plain["params"][0] == pytest.approx(3.5, abs=1e-6)


def test_an_unknown_model_gives_no_fit():
    assert fit_curve([1, 2, 3, 4], [1, 2, 3, 4], kind="cubic") is None
