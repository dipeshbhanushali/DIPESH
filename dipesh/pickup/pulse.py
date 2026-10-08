"""Finding and measuring the extraction pulse in one trace."""

import numpy as np


def analyse_pulse(t, v, nsigma=5.0, baseline_frac=0.10):
    """Find and measure the extraction pulse.

    -> dict: found, baseline, noise, polarity, peak_time_us, amplitude_V,
             area (V·µs, ~ collected charge), width_us (FWHM), n_sigma,
             region (sample indices integrated over)
    """
    n = len(v)
    nb = max(10, int(baseline_frac * n))
    baseline = float(np.median(v[:nb]))
    noise = 1.4826 * float(np.median(np.abs(v[:nb] - baseline))) + 1e-12
    dev = v - baseline
    imax = int(np.argmax(np.abs(dev)))
    polarity = -1 if dev[imax] < 0 else 1
    sig = polarity * dev
    peak = float(sig[imax])
    noise = max(noise, 1e-4)
    n_sig = float(min(peak / noise, 9999.0))

    base = {"baseline": baseline, "noise": noise, "polarity": polarity,
            "n_sigma": n_sig}
    if n_sig < nsigma:
        return {**base, "found": False, "peak_time_us": None,
                "amplitude_V": 0.0, "area": 0.0, "width_us": 0.0,
                "region": None}

    half = peak / 2
    lo = hi = imax
    while lo > 0 and sig[lo] > half:
        lo -= 1
    while hi < n - 1 and sig[hi] > half:
        hi += 1

    thr = 3 * noise
    a = b = imax
    while a > 0 and sig[a] > thr:
        a -= 1
    while b < n - 1 and sig[b] > thr:
        b += 1
    dt = t[1] - t[0] if n > 1 else 1.0

    return {**base, "found": True, "peak_time_us": float(t[imax]),
            "amplitude_V": peak, "area": float(np.sum(sig[a:b + 1]) * dt),
            "width_us": float(t[hi] - t[lo]), "region": (a, b)}
