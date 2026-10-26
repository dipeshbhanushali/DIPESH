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


def box_sum(img, size):
    """Sum of the size x size box around every pixel (at the frame's edge
    the image is mirrored, OpenCV's default)."""
    return cv2.filter2D(img, -1, np.ones((size, size), np.float32))


def local_max(img, size):
    """True where a pixel is the brightest of its size x size neighbourhood,
    within one count (on the 0-255 scale; brighter values are clipped)."""
    k = size if size % 2 else size + 1
    img_u8 = np.clip(img, 0, 255).astype(np.uint8)
    dil = cv2.dilate(img_u8, np.ones((k, k), np.uint8)).astype(np.float32)
    return np.clip(img, 0, 255) >= dil - 1


def brightest_first(xs, ys, values, min_dist):
    """One peak per particle: the candidates in order of brightness, each one
    removing the others closer than min_dist. -> indices of those kept, in
    that order."""
    kept = []
    if len(xs):
        order = np.argsort(values)[::-1]
        sup = np.zeros(len(xs), bool)
        for i in order:
            if sup[i]:
                continue
            kept.append(int(i))
            sup |= np.sqrt((xs - xs[i]) ** 2 + (ys - ys[i]) ** 2) < min_dist
    return kept


def find_spots(img, peak_thresh, box_thresh, min_dist, box=5, local=7,
               spread_min=None):
    """Spots in a background-subtracted image, one per particle: a local
    maximum (local x local), brighter than peak_thresh, whose box x box sum
    is above box_thresh (and, if spread_min is given, whose box sum / peak
    is above it). -> [(x, y, peak, box_sum), ...], brightest first.
    detect() uses the same pieces with box 5 and its own settings."""
    sums = box_sum(img, box)
    mask = local_max(img, local) & (img > peak_thresh) & (sums > box_thresh)
    if spread_min is not None:
        mask &= sums / (img + 1e-6) > spread_min
    ys, xs = np.where(mask)
    return [(int(xs[i]), int(ys[i]), float(img[ys[i], xs[i]]),
             float(sums[ys[i], xs[i]]))
            for i in brightest_first(xs, ys, img[ys, xs], min_dist)]


def candidates(diff, sigma, params=DEFAULT_PARAMS):
    """The pixels that pass every cut, before one-per-particle suppression:
    a local maximum (within nms_size), above the threshold, with a 5x5 sum
    above sum_thresh and a spread (5x5 sum / peak) above spread_min.
    -> (mask, sum5, spread, thresh). The learn lesson shows these same
    arrays (learn/crops.stages)."""
    thresh = (max(params.abs_thresh, params.n_sigma * sigma)
              if params.adaptive else params.abs_thresh)
    sum5 = box_sum(diff, 5)
    spread = sum5 / (diff + 1e-6)
    mask = (local_max(diff, params.nms_size) & (diff > thresh) &
            (sum5 > params.sum_thresh) & (spread > params.spread_min))
    return mask, sum5, spread, thresh


def suppress(diff, sum5, mask, params=DEFAULT_PARAMS):
    """One spot per particle: candidates brightest first, each one removing
    the others closer than min_dist. -> list[Spot]"""
    ys, xs = np.where(mask)
    return [Spot(int(xs[i]), int(ys[i]), float(diff[ys[i], xs[i]]),
                 float(sum5[ys[i], xs[i]]))
            for i in brightest_first(xs, ys, diff[ys, xs], params.min_dist)]


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
