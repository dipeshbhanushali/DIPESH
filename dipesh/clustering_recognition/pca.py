"""
PCA of the spot features - plain numpy, no scikit-learn needed.
"""

import math

import numpy as np


def pca(X):
    """Standardise columns, then principal components by SVD.
    -> (scores [n x k], explained_fraction [k], loadings [k x features])"""
    X = np.asarray(X, float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd < 1e-12] = 1.0
    Z = (X - mu) / sd
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    scores = U * S
    var = S ** 2
    return scores, var / var.sum(), Vt


def spot_matrix(spots, features, log_features=(), isolated_only=True):
    """Rows of feature values, dropping spots with any non-finite value."""
    rows = []
    for s in spots:
        if isolated_only and not s.is_isolated:
            continue
        row = []
        for f in features:
            v = float(getattr(s, f))
            if f in log_features:
                v = math.log10(v) if v > 0 else float("nan")
            row.append(v)
        if all(math.isfinite(v) for v in row):
            rows.append(row)
    return np.asarray(rows, float).reshape(-1, len(features))


def ellipse_points(x, y, n_std=2.0, n=120):
    """Outline of the n_std covariance ellipse, or None with < 5 points."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 5:
        return None
    cov = np.cov(x, y)
    if not np.all(np.isfinite(cov)):
        return None
    lam, vec = np.linalg.eigh(cov)
    lam = np.clip(lam, 0, None)
    t = np.linspace(0, 2 * np.pi, n)
    circ = np.stack([np.cos(t), np.sin(t)])
    pts = vec @ (n_std * np.sqrt(lam)[:, None] * circ)
    return pts[0] + x.mean(), pts[1] + y.mean()
