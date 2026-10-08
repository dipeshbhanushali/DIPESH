"""
Trends across runs: averaging repeats at the same x, and smooth fits.
"""

import math

import numpy as np


def average_xy(xs, ys, bin_width=0.0, error="sem", min_n=1):
    """Collapse repeats at the same x to a mean with an error.
    -> (x, y_mean, y_err, n), sorted by x."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    good = np.isfinite(xs) & np.isfinite(ys)
    xs, ys = xs[good], ys[good]
    if not len(xs):
        return (np.array([]),) * 4
    keys = np.round(xs / bin_width) * bin_width if bin_width > 0 else xs
    xm, ym, ye, ns = [], [], [], []
    for k in np.unique(keys):
        m = keys == k
        n = int(m.sum())
        if n < min_n:
            continue
        yv = ys[m]
        xm.append(xs[m].mean()); ym.append(yv.mean()); ns.append(n)
        sd = yv.std(ddof=1) if n > 1 else 0.0
        ye.append(sd / math.sqrt(n) if error == "sem" else sd)
    o = np.argsort(xm)
    return tuple(np.asarray(v)[o] for v in (xm, ym, ye, ns))


def fit_curve(x, y, yerr=None, kind="quadratic", weighted=True):
    """Fit a smooth model. -> dict(xfit, yfit, params, r2, formula) or None."""
    from scipy.optimize import curve_fit
    x, y = np.asarray(x, float), np.asarray(y, float)
    good = np.isfinite(x) & np.isfinite(y)
    x, y = x[good], y[good]
    if len(x) < 3:
        return None
    sigma = None
    if weighted and yerr is not None:
        e = np.asarray(yerr, float)[good]
        if np.any(e > 0):
            sigma = np.where(e > 0, e, np.median(e[e > 0]))

    models = {
        "linear":      (lambda x, a, b: a * x + b, None, "a·x + b"),
        "quadratic":   (lambda x, a, b, c: a * x * x + b * x + c, None,
                        "a·x² + b·x + c"),
        "exponential": (lambda x, a, b, c: a * np.exp(b * x) + c,
                        [y.max() - y.min(), -1.0 / (np.ptp(x) or 1.0), y.min()],
                        "a·exp(b·x) + c"),
    }
    if kind not in models:
        return None
    f, p0, formula = models[kind]
    import warnings
    try:
        with warnings.catch_warnings():
            # an exactly-determined fit (e.g. 3 points, quadratic) has no
            # covariance estimate; the fit itself is still fine
            warnings.simplefilter("ignore")
            params = curve_fit(f, x, y, p0=p0, sigma=sigma, maxfev=20000)[0]
    except Exception:                             # noqa: BLE001
        return None
    resid = y - f(x, *params)
    ss_tot = np.sum((y - y.mean()) ** 2) or 1.0
    xfit = np.linspace(x.min(), x.max(), 300)
    return {"xfit": xfit, "yfit": f(xfit, *params), "params": params,
            "r2": float(1 - np.sum(resid ** 2) / ss_tot), "formula": formula}
