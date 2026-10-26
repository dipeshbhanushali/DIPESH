"""
Reading data: finding the runs in a folder, loading an image, reading the
Batman parameters of a run.

Files that are read:
  still images   .tif .tiff .png .jpg .jpeg .bmp   (a multi-page TIFF gives
                                                    one item per page)
  videos         .avi .mp4                         (one item per frame; a
                                                    frame is read only when
                                                    it is needed)
Every file or folder that is looked at and not used is reported in
scan(...).skipped with the reason, never dropped silently.
"""

import json
import os
import re
import threading
from dataclasses import dataclass
from typing import NamedTuple

import cv2
import numpy as np

STILL_EXTS = (".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp")
VIDEO_EXTS = (".avi", ".mp4")
IMAGE_EXTS = STILL_EXTS
READ_EXTS = STILL_EXTS + VIDEO_EXTS
TIFF_EXTS = (".tif", ".tiff")
# picture and video formats that are recognised but not read: reported as
# skipped inside run folders too, where other files are the run's metadata
OTHER_MEDIA_EXTS = (".gif", ".webp", ".jp2", ".pgm", ".ppm", ".raw", ".exr",
                    ".hdr", ".heic", ".avif", ".mov", ".mkv", ".wmv", ".mpg",
                    ".mpeg", ".m4v", ".webm")
# files a folder of data may hold that are not data: never reported
SYSTEM_FILES = ("thumbs.db", "desktop.ini")
RUN_PATTERN = re.compile(r"^pbar_run_(\d+)", re.IGNORECASE)


@dataclass
class Item:
    """One image to analyse, with where its run metadata lives."""
    path: str                    # the image or video file
    run_number: int
    folder: str                  # run folder: Batman.json and Picoscope files
    name: str = ""
    frame: int | None = None     # page of a TIFF or frame of a video, from 0

    def __post_init__(self):
        if not self.name:
            self.name = str(self.run_number)

    @property
    def key(self):
        """Unique for each item: the path, and the page or frame if any."""
        return self.path if self.frame is None else f"{self.path}::{self.frame}"


class Skipped(NamedTuple):
    """A file or folder that was looked at and not used, and why."""
    path: str
    reason: str


class Items(list):
    """What scan() finds: a list of Items, plus .skipped, a list of
    Skipped(path, reason) for everything it looked at and did not use."""

    def __init__(self, items=(), skipped=()):
        super().__init__(items)
        self.skipped = list(skipped)


def _ext(path):
    return os.path.splitext(path)[1].lower()


def _hidden(name):
    return name.startswith((".", "~$")) or name.lower() in SYSTEM_FILES


def _listing(folder):
    """-> (files, folders): sorted names in folder, hidden ones left out."""
    files, dirs = [], []
    try:
        names = sorted(os.listdir(folder))
    except (PermissionError, FileNotFoundError, NotADirectoryError):
        return files, dirs
    for n in names:
        if _hidden(n):
            continue
        (dirs if os.path.isdir(os.path.join(folder, n)) else files).append(n)
    return files, dirs


def _why_not_read(path):
    e = _ext(path)
    if not e:
        return "no file extension; DIPESH reads " + " ".join(READ_EXTS)
    return f"{e} files are not read; DIPESH reads " + " ".join(READ_EXTS)


def find_run_folders(root):
    """[(run_number, folder), ...] for every pbar_run_XXXXXX folder."""
    found = []
    for name in os.listdir(root):
        m = RUN_PATTERN.match(name)
        if m and os.path.isdir(os.path.join(root, name)):
            found.append((int(m.group(1)), os.path.join(root, name)))
    return sorted(found)


def _run_media(folder):
    """Every readable image or video in a run folder (or one level down),
    in the order they are preferred: TIFFs, other images, then videos; in
    name order within the folder first, then within each subfolder."""
    try:
        subs = [os.path.join(folder, s) for s in os.listdir(folder)
                if os.path.isdir(os.path.join(folder, s))]
    except (PermissionError, FileNotFoundError):
        return []
    found = []
    for base in [folder] + subs:
        try:
            found += [os.path.join(base, f) for f in sorted(os.listdir(base))
                      if f.lower().endswith(READ_EXTS)]
        except PermissionError:
            pass

    def rank(p):
        e = _ext(p)
        return 0 if e in TIFF_EXTS else 1 if e in STILL_EXTS else 2
    return sorted(found, key=rank)                 # sorted() keeps the order


def find_tiff(folder):
    """Path of the camera TIFF in a run folder (or one level down), or None.
    The first .tif / .tiff in name order is taken."""
    tiffs = [p for p in _run_media(folder) if _ext(p) in TIFF_EXTS]
    return tiffs[0] if tiffs else None


def find_image(folder):
    """The image a run folder is analysed from, or None: the first TIFF as
    find_tiff() picks it, else the first other image, else the first video."""
    media = _run_media(folder)
    return media[0] if media else None


def is_run_folder(path):
    """True for one run's folder: named pbar_run_XXXXXX, or holding the run
    parameter file (Batman.json). Anything else is a folder of loose images."""
    name = os.path.basename(os.path.normpath(path))
    return bool(RUN_PATTERN.match(name)) or os.path.exists(
        os.path.join(path, "Batman.json"))


def _number_in(name, fallback):
    m = RUN_PATTERN.match(name) or re.search(r"(\d{4,})", name)
    return int(m.group(1)) if m else fallback


# ── pages and frames ─────────────────────────────────────────────────────────

def page_count(path):
    """Number of pages of a TIFF (1 for any other still image, and for a
    file that cannot be read: reading it then reports the error)."""
    if _ext(path) not in TIFF_EXTS:
        return 1
    try:
        if hasattr(cv2, "imcount"):
            n = cv2.imcount(path, cv2.IMREAD_UNCHANGED)
        else:                                      # OpenCV before 4.6
            ok, pages = cv2.imreadmulti(path, flags=cv2.IMREAD_UNCHANGED)
            n = len(pages) if ok else 1
    except cv2.error:
        return 1
    return max(int(n), 1)


def frame_count(path):
    """Number of frames of a video, 0 if it cannot be opened. Taken from the
    file's header; if the header does not say, the frames are counted."""
    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            return 0
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if n <= 0:
            n = 0
            while cap.grab():
                n += 1
        return n
    finally:
        cap.release()


def frame_range(frames, n):
    """The frame numbers to use out of n: frames is None (all), a range, or
    (start, stop[, step]) with stop not included, as in Python's range."""
    if frames is None:
        return range(n)
    if not isinstance(frames, range):
        frames = range(*frames)
    return range(n)[slice(frames.start, frames.stop, frames.step)]


def _file_items(path, run_number, folder, name, frames, skipped,
                number_by_frame, single_name=None):
    """The items of one readable file: one for a still image (named
    single_name, or name), one per page of a multi-page TIFF, one per frame
    of a video (named "name [page 3]", "name [frame 12]"). number_by_frame:
    the run number of each page/frame is its page (from 1) or frame (from 0)
    number, for files that are not in a run folder."""
    if _ext(path) in VIDEO_EXTS:
        n = frame_count(path)
        if n == 0:
            skipped.append(Skipped(path, "the video could not be opened"))
            return []
        use = frame_range(frames, n)
        if not len(use):
            skipped.append(Skipped(path, f"no frame in the range asked for "
                                         f"(the video has {n} frames)"))
        return [Item(path, k if number_by_frame else run_number, folder,
                     f"{name} [frame {k}]", frame=k) for k in use]
    n = page_count(path)
    if n == 1:
        return [Item(path, run_number, folder, single_name or name)]
    return [Item(path, k + 1 if number_by_frame else run_number, folder,
                 f"{name} [page {k + 1}]", frame=k) for k in range(n)]


def _run_items(run_number, folder, frames, skipped):
    media = _run_media(folder)
    if not media:
        skipped.append(Skipped(folder, "run folder with no image or video "
                                       "DIPESH reads"))
        return []
    use = media[0]
    for p in media[1:]:
        skipped.append(Skipped(p, "a run is one image; this run uses "
                                  + os.path.basename(use)))
    for base in [folder] + [os.path.join(folder, d) for d in _listing(folder)[1]]:
        for f in _listing(base)[0]:
            if _ext(f) in OTHER_MEDIA_EXTS:
                skipped.append(Skipped(os.path.join(base, f), _why_not_read(f)))
    return _file_items(use, run_number, folder, str(run_number), frames,
                       skipped, number_by_frame=False)


def _loose_items(folder, files, frames, skipped):
    items = []
    for i, f in enumerate(files):
        p = os.path.join(folder, f)
        if not f.lower().endswith(READ_EXTS):
            skipped.append(Skipped(p, _why_not_read(f)))
            continue
        items += _file_items(p, _number_in(f, i), folder, f, frames, skipped,
                             number_by_frame=True,
                             single_name=os.path.splitext(f)[0])
    return items


def _runs_in(folder, frames, skipped):
    items = []
    for rn, f in find_run_folders(folder):
        items += _run_items(rn, f, frames, skipped)
    return items


def scan(path, frames=None):
    """Turn a folder or a file into a list of Items (an Items list: its
    .skipped says what was not used and why).

    Accepts:
      * a folder of pbar_run_XXXXXX folders        -> one item per run
      * a single run folder                        -> one item
      * a folder of loose images or videos         -> one item per image,
                                                      page or frame
      * an image or video file                     -> its items
    Subfolders are not entered here (scan_tree() does that).
    frames: for videos, which frames to use (see frame_range); all if None.
    """
    out = Items()
    if os.path.isfile(path):
        if not path.lower().endswith(READ_EXTS):
            out.skipped.append(Skipped(path, _why_not_read(path)))
            return out
        name = os.path.basename(path)
        folder = os.path.dirname(path)
        rn = _number_in(os.path.basename(folder), _number_in(name, 0))
        in_run = is_run_folder(folder)
        out += _file_items(path, rn, folder, f"{rn}" if rn and in_run else name,
                           frames, out.skipped, number_by_frame=not in_run,
                           single_name=f"{rn}" if rn else name)
        return out

    if not os.path.isdir(path):
        out.skipped.append(Skipped(path, "not found"))
        return out

    files, dirs = _listing(path)
    runs = find_run_folders(path)
    if runs:
        out += _runs_in(path, frames, out.skipped)
        run_dirs = {os.path.basename(f) for _, f in runs}
        for f in files:
            out.skipped.append(Skipped(os.path.join(path, f),
                                       "a file beside pbar_run_ folders; add "
                                       "it on its own to analyse it"))
        for d in dirs:
            if d not in run_dirs:
                out.skipped.append(Skipped(os.path.join(path, d),
                                           "a subfolder; scan_tree() reads "
                                           "subfolders"))
        return out

    if is_run_folder(path):                        # a single run folder
        rn = _number_in(os.path.basename(os.path.normpath(path)), 0)
        out += _run_items(rn, path, frames, out.skipped)
        return out

    out += _loose_items(path, files, frames, out.skipped)
    for d in dirs:
        out.skipped.append(Skipped(os.path.join(path, d),
                                   "a subfolder; scan_tree() reads subfolders"))
    return out


def scan_tree(path, frames=None):
    """Every dataset in a folder, at any depth.

    Each folder holding pbar_run_ folders becomes a dataset of those runs
    (with their Batman and pickup files); each folder holding loose images or
    videos becomes a dataset of them. A folder with both gives two datasets,
    the second named "<folder> (files)". Run folders are not entered further.
    A dataset is named after its folder; when two folders share a name, the
    path from the folder that was added is used instead.

    -> ([(name, Items), ...], [Skipped, ...]): the datasets in folder order,
    and everything that was looked at and not used.
    """
    skipped = []
    if not os.path.isdir(path):
        return [], [Skipped(path, "not a folder")]
    root = os.path.normpath(path)
    found = []                                     # (folder, suffix, Items)

    if is_run_folder(root) and not find_run_folders(root):
        items = Items(_run_items(_number_in(os.path.basename(root), 0), root,
                                 frames, skipped))
        return ([(os.path.basename(root), items)] if items else []), skipped

    def walk(folder):
        files, dirs = _listing(folder)
        runs = find_run_folders(folder)
        if runs:
            items = Items(_runs_in(folder, frames, skipped))
            if items:
                found.append((folder, "", items))
        loose = Items(_loose_items(folder, files, frames, skipped))
        if loose:
            found.append((folder, " (files)" if runs else "", loose))
        run_dirs = {os.path.basename(f) for _, f in runs}
        for d in dirs:
            sub = os.path.join(folder, d)
            if d in run_dirs:
                continue
            if is_run_folder(sub):                 # holds a Batman.json
                items = Items(_run_items(_number_in(d, 0), sub, frames, skipped))
                if items:
                    found.append((sub, "", items))
                continue
            walk(sub)

    walk(root)
    base = os.path.basename(root) or root
    names = [os.path.basename(f) or base for f, _, _ in found]
    out = []
    for (folder, suffix, items), name in zip(found, names):
        if names.count(name) > 1:
            rel = os.path.relpath(folder, os.path.dirname(root))
            name = rel.replace(os.sep, "/")
        out.append((name + suffix, items))
    return out, skipped


# ── reading ──────────────────────────────────────────────────────────────────

_videos = {}                                       # path -> [capture, next frame]
_videos_lock = threading.Lock()
_MAX_OPEN_VIDEOS = 2
# a few frames ahead are decoded and passed over rather than sought: a seek
# in a compressed video decodes again from the last key frame
_SKIP_AHEAD = 16


def _video_frame(path, k):
    """Frame k of a video, read on its own. The last videos read stay open,
    so stepping forward through frames does not seek every time."""
    with _videos_lock:
        entry = _videos.pop(path, None)            # re-inserted as newest
        if entry is None:
            while len(_videos) >= _MAX_OPEN_VIDEOS:
                _videos.pop(next(iter(_videos)))[0].release()
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                return None
            entry = [cap, 0]
        cap = entry[0]
        if entry[1] >= 0 and 0 < k - entry[1] <= _SKIP_AHEAD:
            for _ in range(k - entry[1]):
                cap.grab()
        elif entry[1] != k:
            cap.set(cv2.CAP_PROP_POS_FRAMES, k)
        ok, img = cap.read()
        entry[1] = k + 1 if ok else -1
        _videos[path] = entry
        return img if ok else None


def close_videos():
    """Close the videos kept open by load_image."""
    with _videos_lock:
        while _videos:
            _videos.popitem()[1][0].release()


def _tiff_page(path, k):
    ok, pages = cv2.imreadmulti(path, k, 1, flags=cv2.IMREAD_UNCHANGED)
    return pages[0] if ok and pages else None


def to_grey(img):
    """One channel, float32, from what the file holds.

    Colour: the alpha channel (if any) is dropped. When the three colour
    channels are equal everywhere the image is grey and one of them is kept
    as it is; otherwise grey = 0.299 R + 0.587 G + 0.114 B (ITU-R BT.601, the
    weights OpenCV uses), without rounding.

    Bit depth: integer images keep their values (to_float() later scales by
    the camera's bit depth). Images stored as floating point: NaN and
    infinite pixels become 0; if no pixel is above 1.0 the image is taken as
    a fraction of full scale and multiplied by 255; otherwise the values are
    kept and treated like integer values of the same size.
    """
    stored_float = img.dtype.kind == "f"
    if img.ndim == 3:
        c = img.shape[2]
        if c < 3:                                  # grey, grey + alpha
            img = img[..., 0]
        else:
            b, g, r = img[..., 0], img[..., 1], img[..., 2]
            if np.array_equal(b, g) and np.array_equal(g, r):
                img = b
            else:
                img = (0.114 * b.astype(np.float64) + 0.587 * g
                       + 0.299 * r)
    img = img.astype(np.float32)
    if stored_float:
        img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0)
        if img.size and img.max() <= 1.0:
            img *= 255.0
    return img


def read_raw(path, frame=None):
    """The pixels as the file holds them (colour channels, alpha and bit
    depth as stored), or None. frame as in load_image."""
    if path.lower().endswith(VIDEO_EXTS):
        return _video_frame(path, frame or 0)
    if frame:
        return _tiff_page(path, frame)
    return cv2.imread(path, cv2.IMREAD_UNCHANGED)


def load_image(path, frame=None):
    """Read an image as float32 at its original bit depth. None on failure.
    frame: the page of a multi-page TIFF or the frame of a video, from 0
    (None: a still image's first page, a video's first frame)."""
    img = read_raw(path, frame)
    if img is None:
        return None
    return to_grey(img)


def load_item(item):
    """The image of an Item (its page or frame, if it has one)."""
    return load_image(item.path, item.frame)


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
