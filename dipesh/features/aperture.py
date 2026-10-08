"""
The aperture of one spot, shared by every feature.

Each spot is measured in a small window around it: the same pixels in the
same order as a full-frame mask, so the numbers are identical, at a fraction
of the cost (it is why live detection feels instant). The aperture grows ring
by ring until the light it adds drops below plateau_frac of what is inside.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Aperture:
    """What the features of one spot are computed from. Built once per spot."""
    x: int                       # spot pixel
    y: int
    x0: int                      # top-left corner of the local window
    y0: int
    sub: np.ndarray              # background-subtracted image in the window
    r2: np.ndarray               # squared distance to the spot pixel
    mask: np.ndarray             # pixels inside the grown aperture
    r_used: int                  # radius the aperture grew to
    bg_res: float                # residual background per pixel
    w: np.ndarray                # light per aperture pixel, clipped at zero
    wsum: float                  # sum of w (+1e-9 so it never divides by 0)
    gx: float                    # light-weighted centroid
    gy: float
    dx: np.ndarray               # pixel offsets from the centroid
    dy: np.ndarray


def grow(diff, x, y, bg_res, params):
    """Grow the aperture on the spot at pixel (x, y) until its light
    plateaus (or spot_max_radius is reached). -> Aperture"""
    H, W = diff.shape
    # work in a local window: same numbers, much faster than full-frame
    R = params.spot_max_radius
    x0, x1 = max(0, x - R), min(W, x + R + 1)
    y0, y1 = max(0, y - R), min(H, y + R + 1)
    sub = diff[y0:y1, x0:x1]
    yy, xx = np.ogrid[y0:y1, x0:x1]
    r2 = (xx - x) ** 2 + (yy - y) ** 2

    prev, r_used = 0.0, 1
    for r in range(1, R + 1):
        ap = r2 <= r * r
        lum = float(sub[ap].sum() - bg_res * ap.sum())
        if prev > 0 and (lum - prev) < params.plateau_frac * prev:
            r_used = r
            break
        prev, r_used = lum, r

    ap = r2 <= r_used * r_used

    ly, lx = np.nonzero(ap)
    gx_, gy_ = lx + x0, ly + y0
    w = np.clip(sub[ly, lx] - bg_res, 0, None)
    wsum = w.sum() + 1e-9
    gx = (w * gx_).sum() / wsum
    gy = (w * gy_).sum() / wsum
    dx, dy = gx_ - gx, gy_ - gy
    return Aperture(x, y, x0, y0, sub, r2, ap, r_used, bg_res, w, wsum,
                    gx, gy, dx, dy)
