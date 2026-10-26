"""
How the count falls with storage time: N(t) = N0 exp(-t / tau).

    fit_decay      weighted least squares over any set of points (datasets
                   or series), the errors as weights; tau, N0, their
                   covariance and the reduced chi-squared
    two_point_tau  tau from exactly two points, with its error
"""

import math
from dataclasses import dataclass, field

import numpy as np

PROPAGATIONS = ("first_order", "relative_sum")


@dataclass
class DecayFit:
    n0: float
    tau: float
    covariance: list               # [[var N0, cov], [cov, var tau]]
    chi2: float
    dof: int
    points: list = field(default_factory=list)       # (t, N, error)

    @property
    def n0_err(self):
        return math.sqrt(self.covariance[0][0])

    @property
    def tau_err(self):
        return math.sqrt(self.covariance[1][1])

    @property
    def reduced_chi2(self):
        return self.chi2 / self.dof if self.dof > 0 else float("nan")

    def curve(self, t):
        return self.n0 * np.exp(-np.asarray(t, float) / self.tau)


def fit_decay(times, counts, errors):
    """Fit N0 exp(-t / tau) to points (t in s, N, error of N) by weighted
    least squares, each point weighted by 1 / error^2, the errors taken as
    absolute (the covariance is not rescaled by chi-squared; the reduced
    chi-squared says how well the errors describe the scatter). Starts from
    N0 = the largest count, tau = the mean time; N0 and tau stay positive.
    At least two points with a count above 0 are needed, and every error
    must be above 0 (add an error component to the datasets' tables)."""
    from scipy.optimize import curve_fit
    t = np.asarray(times, float)
    n = np.asarray(counts, float)
    e = np.asarray(errors, float)
    use = np.isfinite(t) & np.isfinite(n) & (n > 0)
    t, n, e = t[use], n[use], e[use]
    if len(t) < 2:
        raise ValueError("a decay fit needs at least two points with a count")
    if not np.all(np.isfinite(e) & (e > 0)):
        raise ValueError("every point of a decay fit needs an error above 0")

    def model(x, n0, tau):
        return n0 * np.exp(-x / tau)

    popt, pcov = curve_fit(model, t, n, p0=[float(n.max()), float(t.mean())],
                           sigma=e, absolute_sigma=True,
                           bounds=([0, 0], [np.inf, np.inf]), maxfev=5000)
    chi2 = float(np.sum(((n - model(t, *popt)) / e) ** 2))
    return DecayFit(float(popt[0]), float(popt[1]), pcov.tolist(), chi2,
                    len(t) - 2, list(zip(t.tolist(), n.tolist(), e.tolist())))


def two_point_tau(t1, n1, e1, t2, n2, e2, propagation="first_order"):
    """tau = (t2 - t1) / ln(n1 / n2) from two points, and its error.

    first_order   the first-order propagation of the two count errors:
                  dtau = tau / ln(n1/n2) x sqrt((e1/n1)^2 + (e2/n2)^2)
    relative_sum  dtau = tau x sqrt((e1/n1)^2 + (e2/n2)^2), the formula some
                  earlier analyses used (larger by 1 / ln(n1/n2) whenever
                  ln(n1/n2) < 1)
    -> (tau, dtau)"""
    if propagation not in PROPAGATIONS:
        raise ValueError(f"propagation is {propagation!r}; it can be "
                         + ", ".join(PROPAGATIONS))
    if n1 <= 0 or n2 <= 0 or n1 == n2:
        raise ValueError("two-point tau needs two different counts above 0")
    ln = math.log(n1 / n2)
    tau = (t2 - t1) / ln
    rel = math.sqrt((e1 / n1) ** 2 + (e2 / n2) ** 2)
    return tau, abs(tau) * rel / (abs(ln) if propagation == "first_order" else 1.0)
