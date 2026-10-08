"""
Image pipeline before detection: hot pixels out, scale by
bit depth, subtract the masked background.
"""

import cv2
import numpy as np

from .params import DEFAULT_PARAMS


def to_float(img):
    """Scale to 0-255 by camera bit depth, never by image content — so a
    threshold means the same physical signal in every run."""
    img = img.astype(np.float32)
    mx = img.max()
    for full_scale in (255.0, 1023.0, 4095.0, 65535.0):
        if mx <= full_scale:
            break
    if full_scale > 255.0:
        img *= 255.0 / full_scale
    return img


def remove_hot_pixels(img, params=DEFAULT_PARAMS):
    """Replace isolated hot pixels by their 3x3 median. -> (image, n)."""
    if params.hotpix_delta <= 0:
        return img, 0
    mx = img.max()
    delta = params.hotpix_delta * (mx / 255.0) if mx > 255 else params.hotpix_delta
    med = cv2.medianBlur(img.astype(np.float32), 3)
    hot = img > (med + delta)
    n = int(hot.sum())
    if n:
        img = img.copy()
        img[hot] = med[hot]
    return img, n


def masked_background(img, params=DEFAULT_PARAMS):
    """Two-pass background: spots are masked out of the second pass so they
    do not raise their own baseline. -> (background, noise_sigma)."""
    k = params.bg_blur_size if params.bg_blur_size % 2 else params.bg_blur_size + 1
    bg1 = cv2.GaussianBlur(img, (k, k), 0)
    resid = img - bg1
    sigma = 1.4826 * np.median(np.abs(resid - np.median(resid)))
    sigma = max(sigma, 1e-3)
    keep = (resid < params.mask_nsigma * sigma).astype(np.float32)
    num = cv2.GaussianBlur(img * keep, (k, k), 0)
    den = cv2.GaussianBlur(keep, (k, k), 0)
    bg2 = num / np.maximum(den, 1e-6)
    bg2[den < 0.05] = bg1[den < 0.05]
    return bg2, sigma


def prepare(img_float, params=DEFAULT_PARAMS):
    """Hot pixels out, normalise, subtract background.
    -> (diff, sigma, n_hot): the background-subtracted image and its noise."""
    img, n_hot = remove_hot_pixels(img_float, params)
    img = to_float(img)
    bg, sigma = masked_background(img, params)
    return np.clip(img - bg, 0, None), float(sigma), n_hot
