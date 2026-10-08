"""Profile slope: how fast the light falls off with distance from the
centroid. Does not depend on the brightness."""

import numpy as np


def profile_slope(ap):
    """Slope of a straight-line fit of log(w) against r over the aperture
    pixels with light; 0 with fewer than 3 such pixels."""
    w, dx, dy = ap.w, ap.dx, ap.dy
    rr = np.sqrt(dx * dx + dy * dy)
    good = w > 0
    return (float(np.polyfit(rr[good], np.log(w[good] + 1e-6), 1)[0])
            if good.sum() >= 3 else 0.0)
