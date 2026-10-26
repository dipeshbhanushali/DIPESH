"""
Synthetic release videos with known answers, written as folders of PNG
frames (lossless, so every count is exact):

    a fixed background (a gradient, a hot pixel) under every frame
    single ions: an integer stamp (ION, light ION_LIGHT) at known places
    an optional pile-up disc filled with the light of a known number of ions
    some frames empty, so the median background is exactly the pattern
"""
import os

import cv2
import numpy as np

SIZE = 200
CENTRE = (100, 100)
OUTER_R = 90
DISC_R = 10
# one ion: peak 60, light 364 over 5 x 5, nothing outside
ION = np.array([[0, 4, 8, 4, 0],
                [4, 24, 36, 24, 4],
                [8, 36, 60, 36, 8],
                [4, 24, 36, 24, 4],
                [0, 4, 8, 4, 0]], np.float32)
ION_LIGHT = float(ION.sum())                       # 364
# ions in the ring, 20 px apart, far from the disc
SITES = [(x, y) for x in range(30, 171, 20) for y in range(30, 171, 20)
         if 30 < np.hypot(x - CENTRE[0], y - CENTRE[1]) < 82]


def pattern():
    """The background every frame has."""
    yy, xx = np.indices((SIZE, SIZE))
    bg = 10 + (xx // 20) + (yy // 25)
    bg[5, 5] = 200                                  # a hot pixel
    return bg.astype(np.float32)


def disc_mask():
    yy, xx = np.indices((SIZE, SIZE))
    return np.hypot(xx - CENTRE[0], yy - CENTRE[1]) <= DISC_R


def disc_per_pixel(disc_ions):
    """The whole counts per disc pixel that hold about disc_ions ions."""
    return float(np.floor(disc_ions * ION_LIGHT / disc_mask().sum()))


def disc_light(disc_ions):
    """The light actually put into the disc for disc_ions ions."""
    return disc_per_pixel(disc_ions) * disc_mask().sum()


def frame(sites, disc_ions=0):
    """One frame: the pattern, ions at sites, and about disc_ions ions'
    worth of light spread evenly over the pile-up disc (disc_light)."""
    img = pattern().copy()
    for x, y in sites:
        img[y - 2:y + 3, x - 2:x + 3] += ION
    if disc_ions:
        img[disc_mask()] += disc_per_pixel(disc_ions)
    return np.clip(img, 0, 255).astype(np.uint8)


def write(folder, plan):
    """plan: [(number of single ions, ions in the disc), ...], one per
    frame; the ions are the first sites. -> folder"""
    os.makedirs(folder, exist_ok=True)
    for k, (n, disc) in enumerate(plan):
        cv2.imwrite(os.path.join(folder, f"frame_{k:05d}.png"),
                    frame(SITES[:n], disc))
    return folder


# the default plan: 6 empty frames and 4 with ions, one with a pile-up
PLAN = [(0, 0), (5, 0), (0, 0), (12, 30), (0, 0), (8, 0), (0, 0), (3, 0),
        (0, 0), (0, 0)]
# the same without the pile-up, for a region with no pile-up disc
PLAN_NO_DISC = [(n, 0) for n, _ in PLAN]
