"""
The numbers behind the image lesson: every intermediate image of the
detection pipeline, and the two windows it is shown through.

Nothing here is a second implementation of the analysis. The stages are the
ones single_image_analysis runs, called in the same order with the same
settings, kept instead of thrown away so they can be drawn.
"""

from dataclasses import dataclass

import cv2
import numpy as np

from ..features import grow
from ..single_image_analysis import (masked_background, remove_hot_pixels,
                                     to_float)


@dataclass
class Stages:
    """The full-frame images detect() goes through, for one frame."""
    camera: np.ndarray           # hot pixels in, 0-255 scale (what the camera saw)
    cleaned: np.ndarray          # hot pixels replaced by their 3x3 median
    hot: np.ndarray              # bool, the pixels that were replaced
    first_pass: np.ndarray       # plain blur: the first background estimate
    masked: np.ndarray           # bool, left out of the second pass (bright)
    background: np.ndarray       # the masked two-pass background estimate
    diff: np.ndarray             # cleaned - background, clipped at 0
    sum5: np.ndarray             # 5x5 sum of diff
    candidates: np.ndarray       # bool, local maxima passing every cut,
                                 # before min-separation suppression
    sigma: float                 # robust noise of the frame
    thresh: float                # threshold actually applied


def stages(img, params):
    """Run the preprocessing of detect() and keep every step. -> Stages"""
    raw = img.astype(np.float32)
    cleaned, _ = remove_hot_pixels(raw, params)
    hot = cleaned != raw                          # the pixels it replaced
    # to_float picks the bit depth from the cleaned frame; the camera frame
    # is put on that same scale so the two can be compared pixel by pixel
    m = float(cleaned.max())
    scale = float(to_float(np.array([m], np.float32))[0]) / m if m > 0 else 1.0
    camera = raw * scale
    cleaned = to_float(cleaned)
    background, sigma = masked_background(cleaned, params)
    diff = np.clip(cleaned - background, 0, None)
    k = params.bg_blur_size if params.bg_blur_size % 2 else params.bg_blur_size + 1
    first_pass = cv2.GaussianBlur(cleaned, (k, k), 0)
    masked = (cleaned - first_pass) >= params.mask_nsigma * sigma
    # the cuts of detection.detect, before the brightest-first suppression
    thresh = (max(params.abs_thresh, params.n_sigma * sigma)
              if params.adaptive else params.abs_thresh)
    sum5 = cv2.filter2D(diff, -1, np.ones((5, 5), np.float32))
    spread = sum5 / (diff + 1e-6)
    n = params.nms_size if params.nms_size % 2 else params.nms_size + 1
    diff_u8 = np.clip(diff, 0, 255).astype(np.uint8)
    dil = cv2.dilate(diff_u8, np.ones((n, n), np.uint8)).astype(np.float32)
    candidates = ((np.clip(diff, 0, 255) >= dil - 1) & (diff > thresh) &
                  (sum5 > params.sum_thresh) & (spread > params.spread_min))
    return Stages(camera, cleaned, hot, first_pass, masked, background, diff,
                  sum5, candidates, float(sigma), float(thresh))


@dataclass(frozen=True)
class Window:
    """A square of the frame, in frame pixel coordinates."""
    x0: int
    y0: int
    x1: int                      # exclusive
    y1: int

    def cut(self, a):
        return a[self.y0:self.y1, self.x0:self.x1]

    @property
    def centre(self):
        return (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2


def window_at(cx, cy, half, shape):
    """The (2 half + 1) square centred on (cx, cy), slid inside the frame."""
    H, W = shape
    side = 2 * half + 1
    x0 = int(min(max(cx - half, 0), max(W - side, 0)))
    y0 = int(min(max(cy - half, 0), max(H - side, 0)))
    return Window(x0, y0, min(x0 + side, W), min(y0 + side, H))


def event_order(spots):
    """Spots to show as the event, cleanest first: isolated ones before
    crowded ones, then the furthest from any other spot, so the first event
    is a spot alone with its own light."""
    return sorted(range(len(spots)),
                  key=lambda i: (not spots[i].is_isolated,
                                 -spots[i].nn_dist, -spots[i].peak))


def quiet_window(spots, half, shape, mcp_region=None):
    """A window with no spot in it, as far from every spot as possible and
    inside the MCP circle when there is one: plain background."""
    H, W = shape
    step = max(half // 2, 4)
    ys, xs = np.mgrid[half:max(H - half, half + 1):step,
                      half:max(W - half, half + 1):step]
    xs, ys = xs.ravel().astype(float), ys.ravel().astype(float)
    if mcp_region is not None:
        cx, cy, r = mcp_region
        inside = (xs - cx) ** 2 + (ys - cy) ** 2 <= (r - half) ** 2
        if inside.any():
            xs, ys = xs[inside], ys[inside]
    if spots:
        pts = np.array([[s.x, s.y] for s in spots], float)
        d = np.sqrt((xs[:, None] - pts[None, :, 0]) ** 2 +
                    (ys[:, None] - pts[None, :, 1]) ** 2).min(1)
        k = int(np.argmax(d))
    elif mcp_region is not None:
        cx, cy, _ = mcp_region
        k = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
    else:
        k = len(xs) // 2
    return window_at(int(xs[k]), int(ys[k]), half, shape)


def aperture(st, spot, bg_res, params):
    """The grown aperture of one spot, as the features see it."""
    return grow(st.diff, spot.x, spot.y, bg_res, params)
