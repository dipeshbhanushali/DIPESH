"""Eccentricity of the light distribution, from its second moments.
Does not depend on the brightness."""

import numpy as np


def second_moments(ap):
    """The covariance of the light about its centroid, as eigenvalues and
    eigenvectors: (lam, vec). lam = [lam1, lam2], lam1 >= lam2, from the
    2x2 eigenproblem solved in closed form; vec[:, k] is the unit vector of
    lam[k], so vec[:, 0] is the long axis. The learn lesson draws its 2 sigma
    ellipse from these, so it shows exactly what eccentricity() uses."""
    w, dx, dy, wsum = ap.w, ap.dx, ap.dy, ap.wsum
    cxx = (w * dx * dx).sum() / wsum
    cyy = (w * dy * dy).sum() / wsum
    cxy = (w * dx * dy).sum() / wsum
    tr, det = cxx + cyy, cxx * cyy - cxy * cxy
    disc = max(tr * tr / 4 - det, 0.0)
    lam1, lam2 = tr / 2 + np.sqrt(disc), tr / 2 - np.sqrt(disc)
    theta = 0.5 * np.arctan2(2 * cxy, cxx - cyy)        # direction of lam1
    c, s = np.cos(theta), np.sin(theta)
    return np.array([lam1, lam2]), np.array([[c, -s], [s, c]])


def eccentricity(ap):
    """sqrt(1 - lam2 / lam1), lam1 >= lam2 the eigenvalues of the covariance
    of the light. 0 for a round spot."""
    lam1, lam2 = second_moments(ap)[0]
    return float(np.sqrt(1 - lam2 / lam1)) if lam1 > 1e-9 else 0.0
