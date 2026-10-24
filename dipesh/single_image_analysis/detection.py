"""
Detecting spots in one image: threshold, shape cuts and non-maximum
suppression, with the per-spot photometry and shape features added on top.
"""

import cv2
import numpy as np

from ..features import measure_spots
from .image_luminosity import image_luminosity
from .params import DEFAULT_PARAMS, DetectionInfo, Spot
from .preprocessing import prepare


def candidates(diff, sigma, params=DEFAULT_PARAMS):
    """The pixels that pass every cut, before one-per-particle suppression:
    a local maximum (within nms_size), above the threshold, with a 5x5 sum
    above sum_thresh and a spread (5x5 sum / peak) above spread_min.
    -> (mask, sum5, spread, thresh). The learn lesson shows these same
    arrays (learn/crops.stages)."""
    thresh = (max(params.abs_thresh, params.n_sigma * sigma)
              if params.adaptive else params.abs_thresh)

    sum5 = cv2.filter2D(diff, -1, np.ones((5, 5), np.float32))
    spread = sum5 / (diff + 1e-6)

    k = params.nms_size if params.nms_size % 2 else params.nms_size + 1
    diff_u8 = np.clip(diff, 0, 255).astype(np.uint8)
    dil = cv2.dilate(diff_u8, np.ones((k, k), np.uint8)).astype(np.float32)
    diff_c = np.clip(diff, 0, 255)
    mask = ((diff_c >= dil - 1) & (diff > thresh) &
            (sum5 > params.sum_thresh) & (spread > params.spread_min))
    return mask, sum5, spread, thresh


def suppress(diff, sum5, mask, params=DEFAULT_PARAMS):
    """One spot per particle: candidates brightest first, each one removing
    the others closer than min_dist. -> list[Spot]"""
    ys, xs = np.where(mask)
    spots = []
    if len(xs):
        order = np.argsort(diff[ys, xs])[::-1]
        sup = np.zeros(len(xs), bool)
        for i in order:
            if sup[i]:
                continue
            cx, cy = int(xs[i]), int(ys[i])
            spots.append(Spot(cx, cy, float(diff[cy, cx]), float(sum5[cy, cx])))
            sup |= np.sqrt((xs - xs[i]) ** 2 + (ys - ys[i]) ** 2) < params.min_dist
    return spots


def detect(img_float, params=DEFAULT_PARAMS, photometry=False):
    """Detect spots in one image.

    photometry=False gives positions, peak and 5x5 sum only.
    photometry=True also measures every spot's luminosity and shape, and the
    image-level integrated luminosity.

    -> (list[Spot], DetectionInfo)
    """
    diff, sigma, n_hot = prepare(img_float, params)
    mask, sum5, _spread, thresh = candidates(diff, sigma, params)
    spots = suppress(diff, sum5, mask, params)

    info = DetectionInfo(sigma=sigma, thresh=float(thresh), hot_pixels=n_hot)
    if photometry:
        image_luminosity(diff, spots, info, params)
        measure_spots(diff, spots, info.bg_residual, params)
    return spots, info
