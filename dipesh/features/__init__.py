"""
Per-spot features: one file per feature, all computed from
the same Aperture.

    aperture        local window + aperture growth to the plateau
    luminosity      light in the aperture
    area            pixels in the aperture
    radial_sigma    RMS radius of the light
    concentration   fraction of the light within 2 px
    eccentricity    elongation from the second moments
    profile_slope   log-light against radius
    isolation       nearest-neighbour distance, is_isolated
"""

import numpy as np

from .aperture import Aperture, grow
from .area import area
from .concentration import concentration
from .eccentricity import eccentricity, second_moments
from .isolation import is_isolated, nn_dist
from .luminosity import luminosity
from .profile_slope import profile_fit, profile_slope
from .radial_sigma import radial_sigma


def measure_spots(diff, spots, bg_res, params):
    """Grow an aperture on each spot until its light plateaus, then measure
    brightness, size and three brightness-independent shape features.
    Fills the fields of every Spot in place."""
    if not spots:
        return
    pts = np.array([[s.x, s.y] for s in spots], float)

    for i, s in enumerate(spots):
        ap = grow(diff, s.x, s.y, bg_res, params)
        s.luminosity = luminosity(ap)
        s.area = area(ap)
        s.radius_used = ap.r_used
        s.radial_sigma = radial_sigma(ap)
        s.concentration = concentration(ap)
        s.eccentricity = eccentricity(ap)
        s.profile_slope = profile_slope(ap)
        s.nn_dist = nn_dist(pts, i)
        s.is_isolated = is_isolated(s.nn_dist, s.radius_used, params)
