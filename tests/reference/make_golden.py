"""
Writes tests/reference/golden.json from the six reference frames in
tests/reference/images/ (synthetic, see make_frames.py). Run it once, from
code that is known to be right. After that the file is the reference: code
changes must reproduce it, never the other way round.

    py tests/reference/make_golden.py
"""
import dataclasses
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from dipesh import DetectionParams, detect, load_image, to_float  # noqa: E402


def plain(v):
    if hasattr(v, "item"):
        return v.item()
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    return v


def frames():
    folder = os.path.join(HERE, "images")
    return sorted(f for f in os.listdir(folder) if f.lower().endswith((".tif", ".tiff")))


def measure(name):
    img = to_float(load_image(os.path.join(HERE, "images", name)))
    spots, info = detect(img, DetectionParams(), photometry=True)
    return {
        "count": len(spots),
        "info": {k: plain(v) for k, v in dataclasses.asdict(info).items()},
        "spots": [{k: plain(v) for k, v in dataclasses.asdict(s).items()} for s in spots],
    }


if __name__ == "__main__":
    out = {"params": dataclasses.asdict(DetectionParams()),
           "frames": {n: measure(n) for n in frames()}}
    with open(os.path.join(HERE, "golden.json"), "w") as f:
        json.dump(out, f, indent=1)
    for n, r in out["frames"].items():
        print(f"{r['count']:4d}  {n}")
