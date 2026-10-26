"""
Ion datasets: a release video (or a folder of frames) with what is known
about it.

    IonDataset        the video, the frames used, the frames left out of
                      the totals, the storage time, the series it belongs to
                      and, if the background comes from elsewhere, where
    find_datasets     every video or folder of frames under a folder
    parse_storage_time  the storage time written in a file or folder name
    parse_frames      "0-1, 5, 10-12" -> [0, 1, 5, 10, 11, 12]
    read_frame        one frame, grey, on the 0-255 scale
    save / load       a dataset and its settings as one JSON file
"""

import json
import os
import re
from dataclasses import asdict, dataclass, field

import cv2
import numpy as np

from ..single_image_analysis import (READ_EXTS, Item, frame_range, read_raw,
                                     scan, scan_tree, to_float, to_grey)
from .params import IonParams

_UNITS = {"h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
          "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
          "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1}
# a number with a unit right after it ("10min", "45 mins", "20s", "1.5 h"),
# not part of a longer word or number
_TIME = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)[ _-]?(hours?|hrs?|h|minutes?|"
                   r"mins?|m|seconds?|secs?|sec|s)(?![a-z])", re.IGNORECASE)


def parse_storage_time(name):
    """The storage time in seconds written in a file or folder name, or None.

    Only a number followed by a unit counts (h, min, s and their long
    forms): "storage_time_10min" is 600, "RF_0_45_storage_time10min" is 600
    (the 0 and 45 have no unit), "45 mins" is 2700, "20s" is 20. Numbers
    written next to each other add up: "1 min 16 sec" is 76. When the name
    holds more than one time, the one after the word "storage" wins,
    otherwise the first. Names without a time give None: set the time by
    hand (IonDataset.storage_time, or the overrides of find_datasets)."""
    stem, ext = os.path.splitext(os.path.basename(str(name)))
    if ext.lower() not in READ_EXTS:                 # "run_1.5h": not a file
        stem += ext
    groups, last_end = [], None
    for m in _TIME.finditer(stem):
        seconds = float(m.group(1)) * _UNITS[m.group(2).lower()]
        between = stem[last_end:m.start()] if last_end is not None else None
        if between is not None and re.fullmatch(r"[ _-]*", between):
            groups[-1][1] += seconds                 # "1 min 16 sec"
        else:
            groups.append([m.start(), seconds])
        last_end = m.end()
    if not groups:
        return None
    at = stem.lower().find("storage")
    if at >= 0:
        after = [g for g in groups if g[0] > at]
        if after:
            return after[0][1]
    return groups[0][1]


def parse_frames(text):
    """Frame numbers from text such as "0-1, 5, 10-12" (ranges include both
    ends) -> sorted list. Empty text gives []."""
    out = set()
    for part in re.split(r"[,;\s]+", str(text).strip()):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            raise ValueError(f"not a frame or a range of frames: {part!r}")
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        out.update(range(min(a, b), max(a, b) + 1))
    return sorted(out)


def format_frames(frames):
    """[0, 1, 5, 10, 11, 12] -> "0-1, 5, 10-12"."""
    frames = sorted(set(frames))
    parts, i = [], 0
    while i < len(frames):
        j = i
        while j + 1 < len(frames) and frames[j + 1] == frames[j] + 1:
            j += 1
        parts.append(str(frames[i]) if i == j else f"{frames[i]}-{frames[j]}")
        i = j + 1
    return ", ".join(parts)


@dataclass
class IonDataset:
    """One release video or folder of frames.

    frames       (start, stop[, step]) of the frames used, as Python's range;
                 None for all
    exclude      frame numbers left out of the totals (every result shows
                 them); the background and, if the settings say so, the
                 calibration still see them
    storage_time seconds, from the name or set by hand; None if unknown
    series       datasets that belong together (a storage-time scan)
    background_source  a separate video or folder for background mode
                 "video", with background_frames like frames
    """
    name: str
    path: str
    frames: tuple | None = None
    exclude: tuple = ()
    storage_time: float | None = None
    series: str = ""
    background_source: str = ""
    background_frames: tuple | None = None
    notes: str = ""

    def items(self):
        """The frames used, as single_image_analysis Items (a video frame,
        a TIFF page or an image file each)."""
        return _items(self.path, self.frames)

    def background_items(self):
        return _items(self.background_source, self.background_frames) \
            if self.background_source else []

    def to_dict(self):
        d = asdict(self)
        d["exclude"] = list(self.exclude)
        return d

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        for k in ("frames", "background_frames"):
            if d.get(k) is not None:
                d[k] = tuple(d[k])
        d["exclude"] = tuple(d.get("exclude", ()))
        return cls(**d)


def _items(path, frames):
    if os.path.isdir(path):
        # a folder of frames: numbered in name order, as a video's
        items = [Item(it.path, k, it.folder, it.name, it.frame)
                 for k, it in enumerate(scan(path))]
        if frames is not None:
            keep = set(frame_range(frames, len(items)))
            items = [it for it in items if it.run_number in keep]
        return items
    return list(scan(path, frames))


def frame_number(item):
    """The frame number of an Item: its frame (videos, TIFF pages) or its
    place in the folder."""
    return item.frame if item.frame is not None else item.run_number


def find_datasets(folder, overrides=None):
    """A dataset for every video, and for every folder of loose images,
    under folder (at any depth). The storage time comes from the file (or
    folder) name; overrides {name or path: seconds} set it by hand. The
    series is the name of the folder the video sits in. -> [IonDataset]"""
    overrides = overrides or {}
    out = []
    groups, _skipped = scan_tree(folder)
    for _name, items in groups:
        videos = sorted({it.path for it in items
                         if it.path.lower().endswith((".avi", ".mp4"))})
        for v in videos:
            name = os.path.splitext(os.path.basename(v))[0]
            out.append(IonDataset(name, v, series=os.path.basename(
                os.path.dirname(v))))
        stills = [it for it in items if it.path not in videos]
        if stills:
            d = os.path.dirname(stills[0].path)
            out.append(IonDataset(os.path.basename(d), d,
                                  series=os.path.basename(os.path.dirname(d))))
    for ds in out:
        t = overrides.get(ds.name, overrides.get(ds.path))
        if t is None:
            t = parse_storage_time(ds.name)
            if t is None and not os.path.isdir(ds.path):
                t = parse_storage_time(os.path.basename(os.path.dirname(ds.path)))
        ds.storage_time = t
    return out


def read_frame(item, grey="exact"):
    """One frame, grey and float32 on the 0-255 scale (integer images keep
    the 1.0 bit-depth rule, single_image_analysis.to_float). grey: exact
    (BT.601 weights, not rounded) or rounded_8bit (rounded to whole counts,
    as OpenCV's cvtColor does for 8-bit colour). None if it cannot be read."""
    raw = read_raw(item.path, item.frame)
    if raw is None:
        return None
    if grey == "rounded_8bit" and raw.ndim == 3 and raw.dtype == np.uint8 \
            and raw.shape[2] in (3, 4):
        code = cv2.COLOR_BGR2GRAY if raw.shape[2] == 3 else cv2.COLOR_BGRA2GRAY
        img = cv2.cvtColor(raw, code).astype(np.float32)
    else:
        img = to_grey(raw)
    return to_float(img)


def save(path, dataset, params):
    """A dataset and its settings in one JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"dataset": dataset.to_dict(), "params": params.to_dict()},
                  f, indent=2)


def load(path):
    """-> (IonDataset, IonParams) from a file written by save()."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return IonDataset.from_dict(d["dataset"]), IonParams.from_dict(d["params"])
