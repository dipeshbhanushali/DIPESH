"""Profile slope: how fast the light falls off with distance from the
centroid. Does not depend on the brightness."""

import numpy as np


def profile_fit(ap):
    """log(light) against distance from the centroid, over the aperture
    pixels with light, and its straight-line fit: (r, log_w, slope,
    intercept). With fewer than 3 such pixels: slope 0, intercept nan. The
    learn lesson plots these, so it shows exactly what profile_slope() uses."""
    w, dx, dy = ap.w, ap.dx, ap.dy
    rr = np.sqrt(dx * dx + dy * dy)
    good = w > 0
    r, log_w = rr[good], np.log(w[good] + 1e-6)
    if good.sum() < 3:
        return r, log_w, 0.0, float("nan")
    slope, intercept = np.polyfit(r, log_w, 1)
    return r, log_w, float(slope), float(intercept)


def profile_slope(ap):
    """Slope of a straight-line fit of log(w) against r over the aperture
    pixels with light; 0 with fewer than 3 such pixels."""
    return profile_fit(ap)[2]
