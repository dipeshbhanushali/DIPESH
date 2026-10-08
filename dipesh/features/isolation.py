"""Isolation: distance to the nearest other spot, and whether that is far
enough for the light in the aperture to belong to one spot only."""

import numpy as np


def nn_dist(pts, i):
    """Distance from spot i to its nearest neighbour; inf for a single spot.
    pts: [n x 2] array of spot positions."""
    if len(pts) > 1:
        dd = np.sqrt(((pts - pts[i]) ** 2).sum(1))
        dd[i] = np.inf
        return float(dd.min())
    return float("inf")


def is_isolated(nearest, radius_used, params):
    """True when the nearest spot is further than isolation_factor x the
    aperture radius."""
    return bool(nearest > params.isolation_factor * radius_used)
