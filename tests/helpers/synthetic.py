"""
Synthetic data with known answers, shared by the tests and the report:
camera frames with planted spots, run folders, PicoScope traces, and single
noise-free Gaussian spots for the analytic feature tests.
"""
import json

import cv2
import numpy as np


def frame(n=7, size=256, amp=200, seed=0, hot=0, sigma=2.2):
    """A noisy frame with n Gaussian spots on a grid. -> (image, [(x, y)])"""
    rng = np.random.default_rng(seed)
    img = rng.normal(12, 1.5, (size, size)).astype(np.float32)
    step = size // 4
    pts = [(step * (1 + i % 3), step * (1 + i // 3)) for i in range(n)]
    yy, xx = np.mgrid[0:size, 0:size]
    for cx, cy in pts:
        img += amp * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma ** 2))
    for i in range(hot):
        img[5 + 3 * i, 5] = 250.0
    return np.clip(img, 0, 255).astype(np.float32), pts


def run_folder(root, rn, n=5, batman=None, **kw):
    """A pbar_run_<rn> folder with one frame (and a Batman.json).
    -> (folder, [(x, y)])"""
    d = root / f"pbar_run_{rn}"
    d.mkdir()
    img, pts = frame(n, **kw)
    cv2.imwrite(str(d / "camera_test.tiff"), img.astype(np.uint8))
    if batman is not None:
        s = " ".join(f"{k}={v}" for k, v in batman.items())
        (d / "Batman.json").write_text(json.dumps([{"Batman": {"__value": s}}]))
    return d, pts


def picoscope(folder, tag, amp=0.006, t_pulse=12.0, rf=0.004):
    """Four channel files of one scope; channel D has a pulse under the RF."""
    dt, n = 0.008, 6000
    t = -10 + np.arange(n) * dt
    rng = np.random.default_rng(1)
    for ch in "ABCD":
        v = rng.normal(0, 0.0002, n)
        if ch == "D":
            v += rf * np.sin(2 * np.pi * 26.92 * t)
            v -= amp * np.exp(-0.5 * ((t - t_pulse) / 0.35) ** 2)
        rec = {f"Picoscope_ch{ch}_{tag}_x": {
            "Y_[V]": {"V": v.tolist()}, "t0": {"__value": -10.0},
            "dt": {"__value": dt}, "Timestamp": {"str": "x"}}}
        (folder / f"Picoscope_ch{ch}_{tag}_x.json").write_text(json.dumps([rec]))


def gaussian_spot(amp=100.0, sx=2.0, sy=None, angle_deg=0.0, size=129,
                  centre=None, offset=0.0):
    """A noise-free elliptical Gaussian, float32, centred on a pixel.

    amp * exp(-(u^2 / (2 sx^2) + v^2 / (2 sy^2))), (u, v) the pixel offsets
    rotated by angle_deg. Its integral is 2 pi amp sx sy.
    -> (image, (cx, cy))
    """
    sy = sx if sy is None else sy
    cx, cy = centre if centre is not None else (size // 2, size // 2)
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    a = np.deg2rad(angle_deg)
    u = (xx - cx) * np.cos(a) + (yy - cy) * np.sin(a)
    v = -(xx - cx) * np.sin(a) + (yy - cy) * np.cos(a)
    img = offset + amp * np.exp(-(u * u / (2 * sx * sx) + v * v / (2 * sy * sy)))
    return img.astype(np.float32), (cx, cy)
