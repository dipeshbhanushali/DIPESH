"""Separation score and best cut between two populations."""
import numpy as np
import pytest

from dipesh import best_threshold, separation_score


def test_separation_and_best_cut():
    rng = np.random.default_rng(0)
    a, b = rng.normal(0, 1, 2000), rng.normal(6, 1, 2000)
    assert separation_score(a, b) > 2.5
    t, ea, eb, swapped = best_threshold(a, b)
    assert 2 < t < 4 and ea < 0.01 and eb < 0.01 and not swapped
    assert best_threshold(b, a)[3]                   # order is detected


def test_separation_score_is_the_mean_difference_over_the_summed_widths():
    """score = |mean_a - mean_b| / (std_a + std_b): means 0 and 6, std 1 and 2 -> 2."""
    a = np.array([-1.0, 1.0] * 50)                   # mean 0, std 1
    b = 6 + np.array([-2.0, 2.0] * 50)               # mean 6, std 2
    assert separation_score(a, b) == pytest.approx(2.0, rel=1e-6)
    assert separation_score(b, a) == pytest.approx(2.0, rel=1e-6)


def test_identical_populations_have_a_score_of_zero():
    a = np.random.default_rng(1).normal(3, 1, 500)
    assert separation_score(a, a) == 0.0


def test_the_best_cut_between_two_equal_gaussians_is_half_way():
    """Equal widths: the cut that minimises the error is (mean_a + mean_b) / 2, and each error is Phi(-d / 2 sigma)."""
    rng = np.random.default_rng(2)
    a, b = rng.normal(0, 1, 20000), rng.normal(3, 1, 20000)
    t, ea, eb, _ = best_threshold(a, b)
    assert t == pytest.approx(1.5, abs=0.15)
    assert ea == pytest.approx(0.0668, abs=0.01)     # Phi(-1.5)
    assert eb == pytest.approx(0.0668, abs=0.01)


def test_disjoint_populations_are_cut_without_error():
    t, ea, eb, _ = best_threshold([1, 2, 3], [7, 8, 9])
    assert 3 <= t < 7 and ea == 0 and eb == 0
