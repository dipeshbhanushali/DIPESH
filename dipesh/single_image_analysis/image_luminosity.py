"""
Image-level photometry: the integrated light inside the MCP
circle and the count derived from it.
"""

import numpy as np


def image_luminosity(diff, spots, info, params):
    """Total light on the MCP, and the luminosity-based count.

    The residual background is the MEAN of spot-free pixels: diff is clipped
    at zero so its noise floor has a positive mean, and only the mean removes
    that without bias when summed over a large region.
    """
    H, W = diff.shape
    yy, xx = np.ogrid[:H, :W]
    if params.mcp_region is not None:
        cx0, cy0, R = params.mcp_region
        region = (xx - cx0) ** 2 + (yy - cy0) ** 2 <= R * R
    else:
        region = np.ones((H, W), bool)

    # masks and apertures are built in a small window around each spot: the
    # same pixels in the same order as a full-frame mask, so the sums are
    # identical, at a fraction of the cost (it matters for live dragging)
    spot_mask = np.zeros((H, W), bool)
    re = params.aperture_radius + 3
    for s in spots:
        x0, x1 = max(0, s.x - re), min(W, s.x + re + 1)
        y0, y1 = max(0, s.y - re), min(H, s.y + re + 1)
        wy, wx = np.ogrid[y0:y1, x0:x1]
        spot_mask[y0:y1, x0:x1] |= (wx - s.x) ** 2 + (wy - s.y) ** 2 <= re * re

    bg_pixels = diff[region & ~spot_mask]
    bg_res = float(np.mean(bg_pixels)) if bg_pixels.size else 0.0
    integrated = float(diff[region].sum() - bg_res * region.sum())

    ap_sum, ra = 0.0, params.aperture_radius
    for s in spots:
        x0, x1 = max(0, s.x - ra), min(W, s.x + ra + 1)
        y0, y1 = max(0, s.y - ra), min(H, s.y + ra + 1)
        wy, wx = np.ogrid[y0:y1, x0:x1]
        ap = (wx - s.x) ** 2 + (wy - s.y) ** 2 <= ra * ra
        ap_sum += float(diff[y0:y1, x0:x1][ap].sum() - bg_res * ap.sum())

    spl = ap_sum / len(spots) if spots else 0.0
    info.integrated_lum = integrated
    info.aperture_lum = ap_sum
    info.pbar_count_lum = integrated / spl if spl > 0 else 0.0
    info.bg_residual = bg_res
