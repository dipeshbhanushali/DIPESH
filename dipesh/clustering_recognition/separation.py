"""
Two-population statistics: how well one feature
separates two sets of spots, and where to cut.
"""

import numpy as np


def separation_score(a, b):
    """|mean_a - mean_b| / (std_a + std_b).  >~1.5 separates cleanly,
    <~0.5 overlaps heavily."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(abs(a.mean() - b.mean()) / (a.std() + b.std() + 1e-9))


def best_threshold(a, b):
    """Cut that minimises the average misidentification of a (low) and b
    (high). -> (threshold, frac_a_above, frac_b_below, swapped)"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    swapped = a.mean() > b.mean()
    if swapped:
        a, b = b, a
    lo, hi = min(a.min(), b.min()), max(a.max(), b.max())
    best_t, best_err = lo, 1.0
    for t in np.linspace(lo, hi, 400):
        e = (np.mean(a > t) + np.mean(b <= t)) / 2
        if e < best_err:
            best_err, best_t = e, t
    return (float(best_t), float(np.mean(a > best_t)),
            float(np.mean(b <= best_t)), swapped)
