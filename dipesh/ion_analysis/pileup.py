"""
The pile-up disc: where ions land on top of each other and cannot be told
apart, their number is estimated from the light, N = S / SIS. Settings:
params.PileupMethod; several methods can run side by side.
"""

import numpy as np


def disc_light(diff, disc, thresholds=()):
    """-> (sum of the disc, its pixels, {threshold: sum of the disc's
    pixels above it})"""
    vals = diff[disc].astype(np.float64)
    return (float(vals.sum()), int(vals.size),
            {t: float(vals[vals > t].sum()) for t in thresholds})


def baseline(method, raw_sums):
    """The disc light of an empty frame, for baseline_sum: a percentile of
    the disc sums over the frames, a fixed value, or 0."""
    if method.baseline == "percentile":
        return float(np.percentile(raw_sums, method.baseline_percentile)) \
            if len(raw_sums) else 0.0
    if method.baseline == "fixed":
        return float(method.baseline_value)
    return 0.0


def signal(method, raw, pixels, above, base, bg_per_pixel):
    """S, the disc light that is counted, for one frame."""
    if method.kind == "threshold_sum":
        s = above[method.pixel_thresh]
    elif method.kind == "baseline_sum":
        s = max(0.0, raw - base)
    else:                                                 # corrected_sum
        s = raw - bg_per_pixel * pixels
    if method.signal_decimals is not None:
        s = round(s, method.signal_decimals)
    return s


def count(method, s, sis):
    """N = S / SIS for one frame (0 without an SIS, or, for corrected_sum,
    when S is below min_sum); rounded as the method says, never below 0."""
    if sis is None or sis <= 0:
        return 0
    if method.kind == "corrected_sum" and s < method.min_sum:
        return 0
    if method.rounding == "nearest":
        return max(0, round(s / sis))                      # halves to even
    return max(0.0, s / sis)
