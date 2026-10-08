"""Eccentricity of the light distribution, from its second moments.
Does not depend on the brightness."""

import numpy as np


def eccentricity(ap):
    """sqrt(1 - lam2 / lam1), lam1 >= lam2 the eigenvalues of the covariance
    of the light. 0 for a round spot."""
    w, dx, dy, wsum = ap.w, ap.dx, ap.dy, ap.wsum
    cxx = (w * dx * dx).sum() / wsum
    cyy = (w * dy * dy).sum() / wsum
    cxy = (w * dx * dy).sum() / wsum
    tr, det = cxx + cyy, cxx * cyy - cxy * cxy
    disc = max(tr * tr / 4 - det, 0.0)
    lam1, lam2 = tr / 2 + np.sqrt(disc), tr / 2 - np.sqrt(disc)
    return float(np.sqrt(1 - lam2 / lam1)) if lam1 > 1e-9 else 0.0
