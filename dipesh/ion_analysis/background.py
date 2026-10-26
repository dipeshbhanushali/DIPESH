"""
The background of a release video: the per-pixel median of a set of its
frames (or of a separate background video), subtracted from every frame
and clipped at 0. Ions are rare at any one pixel, so the median keeps the
detector's fixed pattern (MCP rim, hot pixels, glow) and leaves them out.
"""

import random

import numpy as np


def choose_frames(numbers, mode, n=0, seed=42, light=None):
    """Which frames the background is made of.

    numbers  the frame numbers available, in order
    mode     all, random (n of them, Python's random.Random(seed).sample,
             in frame order) or darkest (the n with the least light; ties
             keep frame order)
    light    {frame number: total light}, needed for darkest
    n of 0, or n at least the number of frames, means all of them.
    -> sorted list of frame numbers
    """
    numbers = list(numbers)
    if mode == "all" or n <= 0 or n >= len(numbers):
        return numbers
    if mode == "random":
        picked = set(random.Random(seed).sample(range(len(numbers)), n))
        return [f for k, f in enumerate(numbers) if k in picked]
    if mode == "darkest":
        if light is None:
            raise ValueError("darkest needs the light of every frame")
        order = sorted(numbers, key=lambda f: light[f])     # stable
        return sorted(order[:n])
    raise ValueError(f"unknown background mode {mode!r}")


def median_of(frames):
    """Per-pixel median of a list of frames (float32 arrays of one size).
    Frames holding whole counts from 0 to 255 are stacked as 8-bit, which
    takes a quarter of the memory and gives the same median. -> float32"""
    frames = list(frames)
    if not frames:
        raise ValueError("no frames to make a background from")
    whole = all(f.min() >= 0 and f.max() <= 255 and np.array_equal(f, np.round(f))
                for f in frames)
    stack = np.stack([f.astype(np.uint8 if whole else np.float32)
                      for f in frames])
    return np.median(stack, axis=0).astype(np.float32)


def subtract(frame, background):
    """clip(frame - background, 0), float32."""
    return np.clip(frame.astype(np.float32) - background, 0.0, None)
