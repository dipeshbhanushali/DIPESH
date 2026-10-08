"""Radial sigma: the light-weighted RMS distance from the centroid."""

import numpy as np


def radial_sigma(ap):
    """sqrt(sum(w r^2) / sum(w)); for a round Gaussian this is sqrt(2) sigma."""
    w, dx, dy = ap.w, ap.dx, ap.dy
    return float(np.sqrt((w * (dx * dx + dy * dy)).sum() / ap.wsum))
