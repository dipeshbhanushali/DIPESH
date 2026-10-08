"""
Realistic test data in the exact on-disk formats the lab writes.

    py tests/helpers/make_testdata.py SOME_NEW_FOLDER

or, from a test:  make_testdata.build(folder, n_pbar=3, n_synthetic=2)

What it makes under the folder:

    pbar_scan/pbar_run_51789X-06-08-2026.JDIR/
        camera_frame.tiff            a reference frame (tests/reference/images)
        Batman.json                  ExtLine_MCP, ExtLine_TrapBiasGround
                                     (100, 200, 300, repeated), PT_TrapTime,
                                     Ecooling_TrapEndcap
        Picoscope_ch{A-D}_PbarExtractionRange10_....json      scope A
        Picoscope_ch{A-D}_PbarExtraction_2_Range10_....json   scope B
                                     channel D: a pulse under the 26.92 MHz
                                     trap RF and its harmonic; A: a gate edge
    background/pbar_run_51800X/      synthetic frames, small faint round spots
    ions/pbar_run_51900X/            synthetic frames, large bright oval spots
    loose_images/frame_00X.tiff      reference frames with no run structure

The folder must be new or empty; nothing is deleted.
"""
import glob
import json
import os
import shutil
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "..", "reference", "images")


def batman(folder, **kw):
    s = " ".join(f"{k}={v}" for k, v in kw.items())
    with open(os.path.join(folder, "Batman.json"), "w") as f:
        json.dump([{"Batman": {"__value": s}}], f)


def scope(folder, tag, t0, amp, t_pulse, rng, rf_amp=0.004):
    dt = 0.008                                  # µs -> 125 MS/s
    n = 6000
    t = t0 + np.arange(n) * dt
    for ch in "ABCD":
        v = rng.normal(0, 0.0002, n)
        if ch == "D":                            # the pickup: RF + a pulse
            v += rf_amp * np.sin(2*np.pi*26.92*t) + 0.3*rf_amp*np.sin(2*np.pi*53.84*t)
            v -= amp * np.exp(-0.5*((t - t_pulse)/0.35)**2)
        elif ch == "A":
            v += 0.5 * (t > t_pulse - 3)         # a gate edge
        else:
            v += 0.02 * np.sin(2*np.pi*0.05*t)
        name = f"Picoscope_ch{ch}_{tag}_20260806_MCP1"
        rec = {name: {
            "Y_[V]": {"V": v.round(6).tolist()},
            "t0": {"__value": float(t0)}, "dt": {"__value": dt},
            "Timestamp": {"str": "2026-08-06 12:46:04"}}}
        with open(os.path.join(folder, name + ".json"), "w") as f:
            json.dump([rec], f)


def frame(n_spots, amp, sigma, seed, ecc=1.0, shape=(1024, 1280)):
    """A synthetic frame: noise plus n_spots Gaussian spots."""
    r = np.random.default_rng(seed)
    h, w = shape
    img = r.normal(14, 1.5, (h, w)).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(n_spots):
        cx, cy = (r.uniform(300 / 1280 * w, 980 / 1280 * w),
                  r.uniform(150 / 1024 * h, 870 / 1024 * h))
        a = amp * r.lognormal(0, 0.25); s = sigma * r.lognormal(0, 0.12)
        img += a*np.exp(-(((xx-cx)/(s*ecc))**2 + ((yy-cy)/s)**2)/2)
    return np.clip(img, 0, 255).astype(np.uint8)


def build(root, n_pbar=6, n_synthetic=5, n_loose=3, synthetic_shape=(1024, 1280)):
    """Write the test data under root (new or empty). -> root"""
    os.makedirs(root, exist_ok=True)
    if os.listdir(root):
        raise SystemExit(f"{root} is not empty")
    rng = np.random.default_rng(7)
    frames = sorted(glob.glob(os.path.join(FRAMES, "frame_*.tiff")))

    # ── pbar runs: the reference frames ────────────────────────────────────
    pdir = os.path.join(root, "pbar_scan"); os.makedirs(pdir)
    biases = [100, 200, 300, 100, 200, 300]
    for i, src in enumerate(frames[:n_pbar]):
        f = os.path.join(pdir, f"pbar_run_{517890+i}-06-08-2026.JDIR"); os.makedirs(f)
        shutil.copy(src, os.path.join(f, "camera_frame.tiff"))
        batman(f, ExtLine_MCP=1650, ExtLine_TrapBiasGround=biases[i], PT_TrapTime=5000,
               Ecooling_TrapEndcap=round(40+5*i, 1))
        amp = 0.004 + 0.002 * (biases[i] / 100)
        scope(f, "PbarExtractionRange10", -10, amp, 12.0 + 0.4*i, rng)
        scope(f, "PbarExtraction_2_Range10", -10, amp*0.6, 18.0, rng)

    # ── synthetic populations for the histogram / PCA views ────────────────
    for name, base, amp, sig, ecc in (("background", 518000, 175, 1.3, 1.0),
                                      ("ions", 519000, 230, 2.6, 1.35)):
        d = os.path.join(root, name); os.makedirs(d)
        for i in range(n_synthetic):
            f = os.path.join(d, f"pbar_run_{base+i}"); os.makedirs(f)
            cv2.imwrite(os.path.join(f, "camera_frame.tiff"),
                        frame(18, amp, sig, base+i, ecc, synthetic_shape))
            batman(f, ExtLine_MCP=1650, ExtLine_TrapBiasGround=100*(1+i%3), PT_TrapTime=5000)

    # ── a folder of loose images (no run structure) ────────────────────────
    ld = os.path.join(root, "loose_images"); os.makedirs(ld)
    for i, src in enumerate(frames[:n_loose]):
        shutil.copy(src, os.path.join(ld, f"frame_{i:03d}.tiff"))
    return root


if __name__ == "__main__":
    root = build(sys.argv[1])
    print("test data in", root)
    for d in sorted(os.listdir(root)):
        print(f"  {d:14s}", len(os.listdir(os.path.join(root, d))), "entries")
