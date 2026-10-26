"""find_spots(): the spot finder shared by detect() and the ion analysis.
Pinned to the ion detector of the old analysis scripts, copied here as it
was, on synthetic frames."""
import cv2
import numpy as np
import pytest

from dipesh.single_image_analysis import find_spots


def old_detector(diff, abs_thresh, sum_thresh, min_dist, box):
    """The detector of the old ion scripts, unchanged (box 5 in the 45 min
    script, 7 in the others)."""
    diff = diff.astype(np.float32)
    s = cv2.filter2D(diff, -1, np.ones((box, box), np.float32))
    dilated = cv2.dilate(diff.astype(np.uint8),
                         np.ones((7, 7), np.uint8)).astype(np.float32)
    mask = (diff >= dilated - 1) & (diff > abs_thresh) & (s > sum_thresh)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return []
    vals, sums = diff[ys, xs], s[ys, xs]
    order = np.argsort(vals)[::-1]
    suppressed = np.zeros(len(xs), dtype=bool)
    kept = []
    for i in order:
        if suppressed[i]:
            continue
        kept.append((int(xs[i]), int(ys[i]), float(vals[i]), float(sums[i])))
        suppressed |= np.sqrt((xs - xs[i]) ** 2 + (ys - ys[i]) ** 2) < min_dist
    return kept


def frame(seed, n=60, size=200):
    """Background-subtracted 8-bit-like frame: noise, Gaussian ions, some
    touching, values in half counts as after a median background."""
    rng = np.random.default_rng(seed)
    img = np.clip(rng.normal(2, 2, (size, size)), 0, None)
    yy, xx = np.mgrid[0:size, 0:size]
    for _ in range(n):
        cx, cy = rng.uniform(5, size - 5, 2)
        img += rng.uniform(15, 120) * np.exp(
            -((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rng.uniform(0.8, 2.0) ** 2))
    return (np.round(np.clip(img, 0, 255) * 2) / 2).astype(np.float32)


@pytest.mark.parametrize("box,peak,box_thresh", [(5, 5, 80), (7, 12, 50),
                                                  (7, 25.5, 110)])
@pytest.mark.parametrize("seed", range(4))
def test_find_spots_equals_the_old_ion_detector(seed, box, peak, box_thresh):
    img = frame(seed)
    assert find_spots(img, peak, box_thresh, 9, box=box) == \
        old_detector(img, peak, box_thresh, 9, box)


def test_inside_a_masked_region_too():
    img = frame(7)
    yy, xx = np.indices(img.shape)
    ring = ((xx - 100) ** 2 + (yy - 100) ** 2 <= 90 ** 2) & \
        ((xx - 100) ** 2 + (yy - 100) ** 2 > 25 ** 2)
    masked = np.where(ring, img, 0.0).astype(np.float32)
    got = find_spots(masked, 12, 50, 9, box=7)
    assert got == old_detector(masked, 12, 50, 9, 7)
    assert all(ring[y, x] for x, y, _, _ in got)


def test_spread_cut_and_separation():
    img = np.zeros((40, 40), np.float32)
    img[10, 10] = 200                       # a hot pixel: no spread
    img[29:32, 29:32] = 60                  # a spot
    img[30, 30] = 100
    spots = find_spots(img, 50, 50, 9, box=5)
    assert [(x, y) for x, y, _, _ in spots] == [(10, 10), (30, 30)]
    spots = find_spots(img, 50, 50, 9, box=5, spread_min=3)
    assert [(x, y) for x, y, _, _ in spots] == [(30, 30)]
    assert spots[0][2] == 100 and spots[0][3] == 100 + 8 * 60
