"""
The ion analysis of one dataset, start to end:

    background   the per-pixel median of the chosen frames
    per frame    subtract it; find the single ions in the region; measure
                 their light for each method's calibration; sum the light in
                 the pile-up disc
    per method   background per pixel, SIS (per frame or one for all),
                 baseline, the ions in the disc of every frame
    totals       over the frames used (excluded frames are left out)

Every frame is read once for the analysis (and once more to choose the
darkest frames, if the background asks for them); nothing is kept in memory
but the background and a few numbers per frame.
"""

import os
from dataclasses import dataclass, field

import numpy as np

from . import aggregate, background as bgmod, calibration as cal, pileup
from .datasets import frame_number, read_frame
from .geometry import masks
from .singles import find_singles


class Cancelled(Exception):
    pass


@dataclass
class MethodInfo:
    """What a pile-up method found for the whole dataset."""
    background_per_pixel: float = 0.0
    sis: float | None = None        # the dataset's SIS, scope frames
    baseline: float = 0.0           # baseline_sum


@dataclass
class IonResult:
    dataset: object
    params: object
    background: np.ndarray
    rows: list                      # aggregate.FrameRow, every frame used
    totals: dict                    # method name -> aggregate.Total
    methods: dict = field(default_factory=dict)   # name -> MethodInfo
    ions: dict = field(default_factory=dict)      # frame -> single ions

    @property
    def excluded(self):
        return [r.frame for r in self.rows if r.excluded]

    def method_names(self):
        return [m.name for m in self.params.methods] or [aggregate.SINGLES_ONLY]


_BACKGROUNDS = {}            # the last few backgrounds, by what they are made of
_KEEP = 3


def _stamp(path):
    """When a file or folder last changed (a changed file is a new key)."""
    try:
        if os.path.isdir(path):
            return max([os.path.getmtime(path)] +
                       [e.stat().st_mtime for e in os.scandir(path)])
        return os.path.getmtime(path)
    except OSError:
        return None


def _background_key(dataset, params):
    b = params.background
    if b.mode == "video":
        src = dataset.background_source
        return ("video", src, _stamp(src), dataset.background_frames,
                params.grey)
    return (b.mode, b.n, b.seed, dataset.path, _stamp(dataset.path),
            dataset.frames, params.grey)


def make_background(dataset, params, items, read, step=None):
    """The background image of a dataset (params.background). The last few
    are kept: changing a detection or calibration setting does not make it
    again."""
    key = _background_key(dataset, params)
    if key in _BACKGROUNDS:
        return _BACKGROUNDS[key]
    bg = _make_background(dataset, params, items, read, step)
    while len(_BACKGROUNDS) >= _KEEP:
        _BACKGROUNDS.pop(next(iter(_BACKGROUNDS)))
    _BACKGROUNDS[key] = bg
    return bg


def forget_backgrounds():
    """Drop the kept backgrounds (when files change on disk)."""
    _BACKGROUNDS.clear()


def _make_background(dataset, params, items, read, step=None):
    b = params.background
    if b.mode == "video":
        src = dataset.background_items()
        if not src:
            raise ValueError(f"{dataset.name}: background mode 'video' needs "
                             "a background source")
        return bgmod.median_of(read(it) for it in src)
    by_number = {frame_number(it): it for it in items}
    light = None
    if b.mode == "darkest" and 0 < b.n < len(items):
        light = {}
        for k, it in enumerate(items):
            light[frame_number(it)] = float(read(it).astype(np.float64).sum())
            if step:
                step()
    chosen = bgmod.choose_frames(list(by_number), b.mode, b.n, b.seed, light)
    return bgmod.median_of(read(by_number[f]) for f in chosen)


def analyse(dataset, params, progress=None, cancelled=None):
    """-> IonResult. progress(done, total) is called as frames are done;
    cancelled() returning True stops it (raises Cancelled)."""
    params.check()
    items = dataset.items()
    if not items:
        raise ValueError(f"{dataset.name}: no frames in {dataset.path}")

    def read(it):
        img = read_frame(it, params.grey)
        if img is None:
            raise ValueError(f"cannot read {it.name} of {dataset.path}")
        return img

    def check():
        if cancelled is not None and cancelled():
            raise Cancelled()

    bg = make_background(dataset, params, items, read, step=check)
    count_mask, disc = masks(bg.shape, params.region)
    excluded = set(dataset.exclude)
    methods = list(params.methods) if disc is not None else []

    # what each method needs from the frames
    measures = {}                                   # key -> CalibrationParams
    for m in methods:
        c = m.calibration
        measures.setdefault((c.measure, c.box, c.radius), c)
    keep_outs = sorted({cal.keep_out_radius(m.calibration) for m in methods
                        if m.calibration.background == "sparsest"})
    thresholds = sorted({m.pixel_thresh for m in methods
                         if m.kind == "threshold_sum"})

    rows, frame_data, ions_by_frame = [], {}, {}
    for k, it in enumerate(items):
        check()
        f = frame_number(it)
        diff = bgmod.subtract(read(it), bg)
        ions = find_singles(diff, count_mask, params.singles)
        d = {"light": {key: cal.measure(diff, ions, c)
                       for key, c in measures.items()},
             "quiet": {r: cal.quiet_median(diff, ions, count_mask, r)
                       for r in keep_outs}}
        if disc is not None:
            d["raw"], d["pixels"], d["above"] = pileup.disc_light(
                diff, disc, thresholds)
        frame_data[f] = d
        ions_by_frame[f] = ions
        rows.append(aggregate.FrameRow(f, len(ions), f in excluded,
                                       d.get("raw", 0.0)))
        if progress:
            progress(k + 1, len(items))

    singles = {r.frame: r.singles for r in rows}
    info = {}
    for m in methods:
        c = m.calibration
        key = (c.measure, c.box, c.radius)
        pool = [r.frame for r in rows if c.use_excluded or not r.excluded]
        bgpp = cal.background_per_pixel(
            c, {f: frame_data[f]["quiet"].get(cal.keep_out_radius(c))
                for f in pool},
            {f: singles[f] for f in pool})
        sis_frame = {}
        for r in rows:
            light, pixels = frame_data[r.frame]["light"][key]
            sis_frame[r.frame] = cal.frame_sis(light - bgpp * pixels,
                                               ions_by_frame[r.frame], c)
        dataset_sis = None
        if c.scope == "frames":
            dataset_sis = cal.frames_sis({f: sis_frame[f][0] for f in pool},
                                         {f: singles[f] for f in pool}, c)
        base = pileup.baseline(m, [frame_data[f]["raw"] for f in pool]) \
            if m.kind == "baseline_sum" else 0.0
        info[m.name] = aggregate_info = MethodInfo(bgpp, dataset_sis, base)
        for r in rows:
            d = frame_data[r.frame]
            own, n_used = sis_frame[r.frame]
            skipped = False
            if c.scope == "frames":
                sis = dataset_sis
            elif own is not None and own > 0:
                sis = own
            elif c.fallback == "fixed":
                sis = float(c.fixed_value)
            else:
                sis, skipped = None, c.fallback == "skip"
            s = pileup.signal(m, d["raw"], d["pixels"], d["above"],
                              aggregate_info.baseline, bgpp)
            inner = pileup.count(m, s, sis)
            r.methods[m.name] = aggregate.MethodFrame(
                sis, n_used, s, inner, r.singles + inner, skipped)

    names = [m.name for m in methods]
    totals = aggregate.totals(rows, names, params.aggregate)
    return IonResult(dataset, params, bg, rows, totals, info, ions_by_frame)


def frame_view(dataset, params, item, background):
    """For the viewer: (background-subtracted frame, single ions, count mask,
    disc mask) of one frame."""
    diff = bgmod.subtract(read_frame(item, params.grey), background)
    count_mask, disc = masks(background.shape, params.region)
    return diff, find_singles(diff, count_mask, params.singles), count_mask, disc
