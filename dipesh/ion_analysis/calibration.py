"""
The single-ion signal (SIS): how much light one ion gives, measured on the
separated single ions, so that a pile-up of overlapping ions can be counted
from its light (pileup.py). Settings: params.CalibrationParams.
"""

import numpy as np


def disc_kernel(radius):
    """Offsets (dy, dx) of the pixels within radius of a centre pixel."""
    r = int(np.floor(radius))
    dy, dx = np.mgrid[-r:r + 1, -r:r + 1]
    keep = np.sqrt(dx ** 2 + dy ** 2) <= radius
    return dy[keep], dx[keep]


def measure(diff, ions, cal):
    """The light of each ion, before any background is taken off, and the
    pixels it was summed over. box: the box x box window centred on the
    ion (cut at the frame's edge); aperture: the pixels within radius.
    -> (light, pixels), float64 arrays"""
    h, w = diff.shape
    light = np.zeros(len(ions))
    pixels = np.zeros(len(ions))
    if cal.measure == "box":
        half = cal.box // 2
        for k, (x, y, _p, _s) in enumerate(ions):
            x1, x2 = max(0, x - half), min(w, x + half + 1)
            y1, y2 = max(0, y - half), min(h, y + half + 1)
            light[k] = float(diff[y1:y2, x1:x2].astype(np.float64).sum())
            pixels[k] = (x2 - x1) * (y2 - y1)
    else:
        dy, dx = disc_kernel(cal.radius)
        for k, (x, y, _p, _s) in enumerate(ions):
            yy, xx = y + dy, x + dx
            inside = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
            light[k] = float(diff[yy[inside], xx[inside]].astype(np.float64).sum())
            pixels[k] = inside.sum()
    return light, pixels


def quiet_median(diff, ions, count_mask, keep_out):
    """Median light per pixel of the region away from every ion (no pixel
    within keep_out px of one), or None if 100 pixels or fewer are left."""
    h, w = diff.shape
    free = np.ones((h, w), bool) if count_mask is None else count_mask.copy()
    dy, dx = disc_kernel(keep_out)
    for x, y, _p, _s in ions:
        yy, xx = y + dy, x + dx
        inside = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
        free[yy[inside], xx[inside]] = False
    vals = diff[free]
    return float(np.median(vals)) if vals.size > 100 else None


def keep_out_radius(cal):
    """How far from an ion the sparsest background stays away."""
    size = cal.radius if cal.measure == "aperture" else cal.box / 2
    return size + cal.margin


def background_per_pixel(cal, quiet_by_frame, singles_by_frame):
    """The light per pixel taken off each measure. sparsest: the mean of the
    quiet medians of the sparsest_frames frames with the fewest single ions
    (ties in frame order) that have one. quiet_by_frame / singles_by_frame:
    {frame: value}, frames in order."""
    if cal.background == "none":
        return 0.0
    if cal.background == "fixed":
        return float(cal.background_value)
    frames = sorted(singles_by_frame, key=lambda f: singles_by_frame[f])
    values = [quiet_by_frame[f] for f in frames[:cal.sparsest_frames]
              if quiet_by_frame.get(f) is not None]
    return float(np.mean(values)) if values else float(cal.background_value)


def _stat(values, how):
    return float(np.median(values) if how == "median" else np.mean(values))


def frame_sis(light, ions, cal):
    """The SIS of one frame from its ions' light (background already taken
    off). -> (sis or None, number of ions used)"""
    light = np.asarray(light, float)
    use = np.ones(len(light), bool)
    if cal.positive:
        use &= light > 0
    if not use.any():
        return None, 0
    if cal.select == "above_median":
        above = use & (light > np.median(light[use]))
        if above.any():
            use = above
    elif cal.select == "isolated":
        xs = np.array([i[0] for i in ions], float)
        ys = np.array([i[1] for i in ions], float)
        alone = np.zeros(len(light), bool)
        for k in range(len(light)):
            d = np.hypot(xs - xs[k], ys - ys[k])
            d[k] = np.inf
            alone[k] = d.min() >= cal.isolation_px if len(d) > 1 else True
        use &= alone
        if not use.any():
            return None, 0
    sis = _stat(light[use], cal.statistic)
    if cal.decimals is not None:
        sis = round(sis, cal.decimals)
    return sis, int(use.sum())


def frames_sis(sis_by_frame, singles_by_frame, cal):
    """One SIS for the dataset (scope frames): frames_statistic of the
    frames' SIS over frames with at least min_ions single ions and an SIS
    above 0, or None."""
    values = [s for f, s in sis_by_frame.items()
              if s is not None and s > 0 and singles_by_frame[f] >= cal.min_ions]
    return _stat(values, cal.frames_statistic) if values else None
