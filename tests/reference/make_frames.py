"""
Writes the six reference frames, tests/reference/images/frame_1.tiff ... 6.

They are synthetic (no camera data is shipped) but built like a real frame of
an MCP / phosphor screen: 1280 x 1024 pixels, 8 bit, Gaussian noise, a slowly
varying glow inside the MCP circle (centre 640, 512, radius 430), Gaussian
spots of varied brightness and width (sigma 1.5 to 3 px) gathered towards the
centre, a few crowded pairs, a few hot pixels. One frame is nearly empty and
one is busy.

The seed is fixed, so the frames come out the same every time:

    py tests/reference/make_frames.py
    py tests/reference/make_golden.py      (then: the numbers they must give)
"""
import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SHAPE = (1024, 1280)
MCP = (640, 512, 430)                    # cx, cy, r
SEED = 20261008

# per frame: spots planted, of which partners of a crowded pair, hot pixels
FRAMES = [(25, 3, 4), (45, 5, 5), (34, 4, 3), (28, 2, 4), (3, 0, 2), (7, 1, 3)]


def background(rng):
    """Dark outside the MCP; inside, a faint glow with a slow gradient."""
    h, w = SHAPE
    cx, cy, r = MCP
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rho = np.hypot(xx - cx, yy - cy)
    tilt = rng.uniform(-1.5, 1.5, 2)
    glow = (4.0 + tilt[0] * (xx - cx) / r + tilt[1] * (yy - cy) / r
            + 3.0 * np.exp(-rho ** 2 / (2 * 260.0 ** 2)))
    edge = 1.0 / (1.0 + np.exp(np.clip((rho - r) / 3.0, -50, 50)))  # soft rim
    return 9.0 + glow * edge


def add_spot(img, x, y, amp, sigma):
    """Add one Gaussian spot, in a window of 6 sigma around it."""
    h, w = img.shape
    k = int(np.ceil(6 * sigma))
    x0, x1 = max(0, int(x) - k), min(w, int(x) + k + 1)
    y0, y1 = max(0, int(y) - k), min(h, int(y) + k + 1)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    img[y0:y1, x0:x1] += amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2)
                                      / (2 * sigma ** 2))


def make_frame(k, n_spots, n_partners, n_hot):
    rng = np.random.default_rng(SEED + k)
    cx, cy, r = MCP
    img = background(rng) + rng.normal(0, 1.5, SHAPE).astype(np.float32)

    centres = []
    for i in range(n_spots - n_partners):
        if i % 4 == 3:                                   # scattered on the MCP
            a, d = rng.uniform(0, 2 * np.pi), 0.85 * r * np.sqrt(rng.uniform())
            centres.append((cx + d * np.cos(a), cy + d * np.sin(a)))
        else:                                            # the central cluster
            centres.append((cx + rng.normal(0, 75), cy + rng.normal(0, 75)))
    for i in range(n_partners):                          # crowded pairs
        x, y = centres[i]
        a, d = rng.uniform(0, 2 * np.pi), rng.uniform(13, 18)
        centres.append((x + d * np.cos(a), y + d * np.sin(a)))

    for x, y in centres:
        add_spot(img, x, y, amp=rng.uniform(170, 300),
                 sigma=rng.uniform(1.5, 3.0))
    for _ in range(n_hot):
        a, d = rng.uniform(0, 2 * np.pi), r * np.sqrt(rng.uniform())
        img[int(cy + d * np.sin(a)), int(cx + d * np.cos(a))] = 250.0
    return np.clip(np.rint(img), 0, 255).astype(np.uint8)


if __name__ == "__main__":
    folder = os.path.join(HERE, "images")
    os.makedirs(folder, exist_ok=True)
    for k, spec in enumerate(FRAMES, 1):
        path = os.path.join(folder, f"frame_{k}.tiff")
        cv2.imwrite(path, make_frame(k, *spec))
        print(f"frame_{k}.tiff  {spec[0]} spots planted, {spec[1]} in crowded "
              f"pairs, {spec[2]} hot pixels")
