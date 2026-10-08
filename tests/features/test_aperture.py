"""The aperture: grown ring by ring until the light plateaus."""
import numpy as np
import pytest

import validation as v
from dipesh import DetectionParams
from dipesh.features import grow


def test_the_radius_grows_with_the_spot_size():
    """R(sigma) is non-decreasing, and larger for sigma = 3 than for 1.5."""
    radii = [v.radius_for(s) for s in (1.5, 2.0, 2.5, 3.0)]
    assert radii == sorted(radii) and radii[-1] > radii[0]


@pytest.mark.parametrize("case", v.aperture_radius_cases(), ids=lambda c: c.label)
def test_the_radius_is_where_a_ring_adds_less_than_plateau_frac(case):
    """R = first r with L(r) - L(r-1) < 0.02 L(r-1), L(r) = 1 - exp(-r^2 / 2 sigma^2); within 1 px."""
    assert case.ok, case


@pytest.mark.parametrize("max_radius", [5, 8, 12])
def test_the_radius_stops_at_spot_max_radius(max_radius):
    """A spot of sigma = 6 px never plateaus within 12 px: R = spot_max_radius."""
    assert v.radius_for(6.0, spot_max_radius=max_radius) == max_radius


@pytest.mark.parametrize("sigma", v.SIGMAS)
def test_a_larger_plateau_frac_never_gives_a_larger_radius(sigma):
    """R(plateau_frac) is non-increasing."""
    radii = [v.radius_for(sigma, plateau_frac=f, spot_max_radius=20)
             for f in (0.005, 0.02, 0.05, 0.2)]
    assert radii == sorted(radii, reverse=True)


def test_the_centroid_is_the_centre_of_the_spot():
    """Centroid = sum(w x) / sum(w): the centre of a Gaussian placed 0.3 px
    right and 0.2 px down of the pixel, to 1e-3 px."""
    ap = v.aperture(sx=2.0, shift=(0.3, 0.2))
    c = 129 // 2
    assert ap.gx == pytest.approx(c + 0.3, abs=1e-3)
    assert ap.gy == pytest.approx(c + 0.2, abs=1e-3)


def test_the_local_window_gives_the_same_numbers_as_the_full_frame(
        gaussian_spot):
    """The aperture mask built in the window equals the full-frame mask."""
    img, (cx, cy) = gaussian_spot(100, 2.0)
    ap = grow(img, cx, cy, 0.0, DetectionParams())
    yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
    full = (xx - cx) ** 2 + (yy - cy) ** 2 <= ap.r_used ** 2
    assert int(full.sum()) == int(ap.mask.sum())
    assert float(img[full].sum()) == float(ap.sub[ap.mask].sum())


def test_a_spot_at_the_image_edge_uses_the_pixels_that_exist(gaussian_spot):
    img, _ = gaussian_spot(100, 2.0, size=65, centre=(2, 30))
    ap = grow(img, 2, 30, 0.0, DetectionParams())
    assert ap.x0 == 0 and ap.mask.shape[1] == 2 + 12 + 1
