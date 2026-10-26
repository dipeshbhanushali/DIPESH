"""
The region where single ions are counted and the optional pile-up disc
(params.RegionParams): masks over the frame.
"""

import numpy as np


def masks(shape, region):
    """-> (count, disc): boolean masks of the frame where single ions are
    counted and of the pile-up disc. count is None for the whole frame;
    disc is None when there is no pile-up region (kind other than ring)."""
    h, w = shape
    kind = region.kind
    if kind == "frame":
        return None, None
    yy, xx = np.indices((h, w))
    if kind == "rect":
        m = np.zeros((h, w), bool)
        m[max(region.y0, 0):max(region.y1, 0),
          max(region.x0, 0):max(region.x1, 0)] = True
        return m, None
    r_out = np.sqrt((xx - region.cx) ** 2 + (yy - region.cy) ** 2)
    if kind == "circle":
        return r_out <= region.r, None
    if kind == "ring":
        r_in = np.sqrt((xx - region.inner_cx) ** 2 + (yy - region.inner_cy) ** 2)
        return (r_out <= region.r) & (r_in > region.inner_r), r_in <= region.inner_r
    raise ValueError(f"unknown region {kind!r}")


def restrict(diff, count_mask):
    """The frame as single-ion detection sees it: dark (0) outside the
    region."""
    if count_mask is None:
        return diff
    return np.where(count_mask, diff, 0.0).astype(np.float32)
