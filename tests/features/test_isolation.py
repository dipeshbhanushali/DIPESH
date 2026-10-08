"""Isolation: nearest-neighbour distance and the is_isolated flag."""
import numpy as np
import pytest

from dipesh import DetectionParams, Spot
from dipesh.features import is_isolated, measure_spots, nn_dist


@pytest.mark.parametrize("d", [5, 13, 40])
def test_two_spots_at_distance_d_have_nn_dist_d(gaussian_spot, d):
    """nn_dist = d for two spots d px apart (exact)."""
    a, (cx, cy) = gaussian_spot(100, 1.5)
    b, _ = gaussian_spot(100, 1.5, centre=(cx + d, cy))
    spots = [Spot(cx, cy, 100.0, 0.0), Spot(cx + d, cy, 100.0, 0.0)]
    measure_spots(a + b, spots, 0.0, DetectionParams())
    assert spots[0].nn_dist == d and spots[1].nn_dist == d


def test_nn_dist_is_the_distance_to_the_nearest_of_several():
    """nn_dist_i = min over j != i of |p_i - p_j|: 3-4-5 triangle."""
    pts = np.array([[0, 0], [3, 0], [0, 4]], float)
    assert [nn_dist(pts, i) for i in range(3)] == [3.0, 3.0, 4.0]


def test_a_single_spot_has_infinite_nn_dist_and_is_isolated(gaussian_spot):
    """One spot: nn_dist = inf, is_isolated = True."""
    img, (cx, cy) = gaussian_spot(100, 2.0)
    s = Spot(cx, cy, 100.0, 0.0)
    measure_spots(img, [s], 0.0, DetectionParams())
    assert s.nn_dist == float("inf") and s.is_isolated is True


@pytest.mark.parametrize("factor, radius", [(2.0, 6), (2.0, 7), (1.5, 8),
                                            (3.0, 5)])
def test_is_isolated_flips_exactly_at_factor_times_radius(factor, radius):
    """is_isolated = nn_dist > isolation_factor * radius_used (strictly)."""
    p = DetectionParams(isolation_factor=factor)
    edge = factor * radius
    assert is_isolated(edge, radius, p) is False
    assert is_isolated(np.nextafter(edge, np.inf), radius, p) is True
    assert is_isolated(edge - 1, radius, p) is False


def test_is_isolated_in_an_image_follows_the_measured_radius(gaussian_spot):
    """Two sigma = 1.5 spots (radius 6): crowded at 12 px, isolated at 13 px."""
    for d, want in ((12, False), (13, True)):
        a, (cx, cy) = gaussian_spot(100, 1.5)
        b, _ = gaussian_spot(100, 1.5, centre=(cx + d, cy))
        spots = [Spot(cx, cy, 100.0, 0.0), Spot(cx + d, cy, 100.0, 0.0)]
        measure_spots(a + b, spots, 0.0, DetectionParams())
        assert spots[0].radius_used == 6
        assert spots[0].is_isolated is want
