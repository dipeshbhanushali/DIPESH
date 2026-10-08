"""
Reading data: finding the runs in a folder, loading an image, reading the
Batman parameters of a run.
"""

import json
import os
import re
from dataclasses import dataclass

import cv2
import numpy as np

IMAGE_EXTS = (".tif", ".tiff", ".png")
RUN_PATTERN = re.compile(r"^pbar_run_(\d+)", re.IGNORECASE)


@dataclass
class Item:
    """One image to analyse, with where its run metadata lives."""
    path: str                    # the image file
    run_number: int
    folder: str                  # run folder: Batman.json and Picoscope files
    name: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = str(self.run_number)


def find_run_folders(root):
    """[(run_number, folder), ...] for every pbar_run_XXXXXX folder."""
    found = []
    for name in os.listdir(root):
        m = RUN_PATTERN.match(name)
        if m and os.path.isdir(os.path.join(root, name)):
            found.append((int(m.group(1)), os.path.join(root, name)))
    return sorted(found)


def find_tiff(folder):
    """Path of the camera TIFF in a run folder (or one level down), or None.
    The first .tif / .tiff in name order is taken."""
    try:
        subs = [os.path.join(folder, s) for s in os.listdir(folder)
                if os.path.isdir(os.path.join(folder, s))]
    except (PermissionError, FileNotFoundError):
        return None
    for base in [folder] + subs:
        try:
            for f in sorted(os.listdir(base)):
                lf = f.lower()
                if lf.endswith((".tif", ".tiff")):
                    return os.path.join(base, f)
        except PermissionError:
            pass
    return None


def is_run_folder(path):
    """True for one run's folder: named pbar_run_XXXXXX, or holding the run
    parameter file (Batman.json). Anything else is a folder of loose images."""
    name = os.path.basename(os.path.normpath(path))
    return bool(RUN_PATTERN.match(name)) or os.path.exists(
        os.path.join(path, "Batman.json"))


def _number_in(name, fallback):
    m = RUN_PATTERN.match(name) or re.search(r"(\d{4,})", name)
    return int(m.group(1)) if m else fallback


def scan(path):
    """Turn a folder or a file into a list of Items.

    Accepts:
      * a folder of pbar_run_XXXXXX folders        -> one item per run
      * a single run folder                        -> one item
      * a folder of loose .tif/.tiff/.png images   -> one item per image
      * an image file                              -> one item
    """
    if os.path.isfile(path):
        if not path.lower().endswith(IMAGE_EXTS):
            return []
        name = os.path.basename(path)
        folder = os.path.dirname(path)
        rn = _number_in(os.path.basename(folder), _number_in(name, 0))
        return [Item(path, rn, folder, f"{rn}" if rn else name)]

    if not os.path.isdir(path):
        return []

    runs = find_run_folders(path)
    if runs:
        items = []
        for rn, folder in runs:
            tif = find_tiff(folder)
            if tif:
                items.append(Item(tif, rn, folder))
        return items

    tif = find_tiff(path) if is_run_folder(path) else None
    if tif:                                       # a single run folder
        rn = _number_in(os.path.basename(os.path.normpath(path)), 0)
        return [Item(tif, rn, path)]

    files = sorted(f for f in os.listdir(path) if f.lower().endswith(IMAGE_EXTS))
    return [Item(os.path.join(path, f), _number_in(f, i), path,
                 os.path.splitext(f)[0])
            for i, f in enumerate(files)]


def load_image(path):
    """Read an image as float32 at its original bit depth. None on failure."""
    img = cv2.imread(path, cv2.IMREAD_ANYDEPTH)
    if img is None:
        return None
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img.astype(np.float32)


def parse_batman(folder):
    """All numeric parameters from a run's Batman.json, or {}."""
    path = os.path.join(folder, "Batman.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        cmd = data[0]["Batman"]["__value"]
        return {k: float(v)
                for k, v in re.findall(r"(\w+)=([-\d.]+)(?:\s|$)", cmd)}
    except Exception:                             # noqa: BLE001
        return {}
