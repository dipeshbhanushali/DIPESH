"""PCA of the spot features, the feature matrix and the covariance ellipse."""
import math

import numpy as np
import pytest

from dipesh import Spot, pca
from dipesh.clustering_recognition import (ellipse_points,
                                                        spot_matrix)


def test_pca_finds_the_direction_of_variance():
    rng = np.random.default_rng(0)
    z = rng.normal(size=500)
    X = np.c_[z, 2 * z + 0.01 * rng.normal(size=500), rng.normal(size=500)]
    scores, ev, load = pca(X)
    assert ev[0] > 0.6 and abs(ev.sum() - 1) < 1e-9
    assert abs(abs(load[0][0]) - abs(load[0][1])) < 0.05   # first two tie


def test_pca_of_two_fully_correlated_columns_has_one_component():
    """y = 3x: explained variance (1, 0), loading (1, 1) / sqrt(2)."""
    x = np.linspace(-1, 1, 50)
    scores, ev, load = pca(np.c_[x, 3 * x])
    assert ev[0] == pytest.approx(1.0) and ev[1] == pytest.approx(0.0, abs=1e-12)
    assert np.abs(load[0]) == pytest.approx([2 ** -0.5, 2 ** -0.5])


def test_pca_scores_are_uncorrelated_and_carry_the_variance():
    """Columns are standardised first: total variance of the scores = number of columns."""
    X = np.random.default_rng(3).normal(size=(400, 4)) @ np.diag([5, 2, 1, 0.5])
    scores, ev, _ = pca(X)
    cov = np.cov(scores.T, bias=True)
    assert np.allclose(cov - np.diag(np.diag(cov)), 0, atol=1e-9)
    assert np.trace(cov) == pytest.approx(4.0)
    assert list(ev) == sorted(ev, reverse=True)


def test_a_constant_column_does_not_break_pca():
    X = np.c_[np.arange(10.0), np.full(10, 7.0)]
    scores, ev, _ = pca(X)
    assert np.all(np.isfinite(scores)) and ev[0] == pytest.approx(1.0)


def spot(lum, iso=True, sigma=2.0):
    s = Spot(0, 0, 100.0, 500.0)
    s.luminosity, s.radial_sigma, s.is_isolated = lum, sigma, iso
    return s


def test_spot_matrix_keeps_isolated_finite_spots_only():
    spots = [spot(100.0), spot(200.0, iso=False), spot(float("nan")),
             spot(400.0)]
    X = spot_matrix(spots, ["luminosity", "radial_sigma"])
    assert X.tolist() == [[100.0, 2.0], [400.0, 2.0]]
    assert len(spot_matrix(spots, ["luminosity"], isolated_only=False)) == 3


def test_spot_matrix_takes_log10_of_the_log_features():
    X = spot_matrix([spot(1000.0), spot(0.0)], ["luminosity", "radial_sigma"],
                    log_features={"luminosity"})
    assert X.tolist() == [[3.0, 2.0]]                # log of 0 is dropped


def test_spot_matrix_of_nothing_has_the_right_shape():
    assert spot_matrix([], ["luminosity", "peak"]).shape == (0, 2)


def test_the_ellipse_is_the_n_sigma_contour_of_the_covariance():
    """Points on a circle of radius 1: covariance = I n / (2 (n - 1)), so the 2 sigma ellipse is a circle of radius 2 sqrt(n / (2 (n - 1)))."""
    n = 200
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ex, ey = ellipse_points(5 + np.cos(t), -3 + np.sin(t), n_std=2.0)
    r = np.hypot(ex - 5, ey + 3)
    assert np.allclose(r, 2 * math.sqrt(n / (2 * (n - 1))), rtol=1e-9)


def test_the_ellipse_needs_five_points():
    assert ellipse_points([1, 2, 3, 4], [1, 2, 3, 5]) is None
