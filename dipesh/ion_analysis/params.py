"""
Every setting of the ion analysis, with its default. IonParams is frozen:
change a setting with dataclasses.replace() (or IonParams.with_()). It
saves to and loads from JSON, alone or with a dataset (datasets.py).

    grey         how a colour frame becomes grey
    background   the per-pixel median background subtracted from each frame
    region       where single ions are looked for, and the optional pile-up
                 disc where they overlap
    singles      how a single ion is found
    methods      ways of estimating the ions in the pile-up disc, each with
                 its own single-ion calibration (several can run side by side)
    aggregate    how the frames add up to one count
"""

import dataclasses
import json
from dataclasses import dataclass, field, fields

GREY_RULES = ("exact", "rounded_8bit")
BACKGROUND_MODES = ("darkest", "random", "all", "video")
REGIONS = ("frame", "rect", "circle", "ring")
MEASURES = ("box", "aperture")
SELECTIONS = ("all", "above_median", "isolated")
STATISTICS = ("median", "mean")
SCOPES = ("frame", "frames")
FALLBACKS = ("none", "fixed", "skip")
SIGNAL_BACKGROUNDS = ("none", "fixed", "sparsest")
PILEUP_KINDS = ("threshold_sum", "baseline_sum", "corrected_sum")
BASELINES = ("none", "percentile", "fixed")
ROUNDINGS = ("none", "nearest")
AGGREGATE_RULES = ("sum", "active")
TIES = ("reading", "numpy1")


@dataclass(frozen=True)
class BackgroundParams:
    """The background: per-pixel median of a set of frames.

    mode    darkest  the n frames with the least light
            random   n frames picked at random (with seed)
            all      every frame used
            video    every frame of a separate background video or folder
                     (the dataset's background_source)
    n       frames for darkest and random; all of them if there are fewer,
            or if n is 0
    """
    mode: str = "darkest"
    n: int = 50
    seed: int = 42


@dataclass(frozen=True)
class RegionParams:
    """Where single ions are counted, and the optional pile-up disc.

    kind    frame   the whole frame
            rect    the rectangle x0, y0, x1, y1 (x1, y1 not included)
            circle  the circle cx, cy, r
            ring    the circle cx, cy, r minus the pile-up disc
                    inner_cx, inner_cy, inner_r: single ions are counted in
                    the ring, the disc is estimated by the methods
    Outside the region the frame counts as dark (0) for single ions.
    """
    kind: str = "frame"
    x0: int = 0
    y0: int = 0
    x1: int = 0
    y1: int = 0
    cx: float = 0.0
    cy: float = 0.0
    r: float = 0.0
    inner_cx: float = 0.0
    inner_cy: float = 0.0
    inner_r: float = 0.0

    @property
    def pileup(self):
        return self.kind == "ring"


@dataclass(frozen=True)
class SinglesParams:
    """A single ion: a local maximum (local x local px) brighter than
    peak_thresh whose box x box sum is above box_thresh; two ions are at
    least min_dist px apart (brightest first). Values on the 0-255 scale of
    the background-subtracted frame. spread_min (box sum / peak) rejects
    hot pixels; None leaves the cut out. ties: which of two equally bright
    candidates comes first (tie_order.py): reading (row by row) or numpy1."""
    peak_thresh: float = 12.0
    box: int = 7
    box_thresh: float = 50.0
    min_dist: float = 9.0
    local: int = 7
    spread_min: float | None = None
    ties: str = "reading"


@dataclass(frozen=True)
class CalibrationParams:
    """The single-ion signal (SIS): the light one ion gives.

    measure      box       sum of the box x box window centred on the ion
                 aperture  sum of the pixels within radius of the ion
    background   light per pixel taken off each measure:
                 none, fixed (background_value), or sparsest: the median
                 of the region's pixels away from ions (radius + margin px)
                 in the sparsest_frames frames with the fewest single ions,
                 averaged (background_value when none qualifies)
    positive     keep only measures above 0
    select       all, above_median (above the frame's median), isolated
                 (no other ion within isolation_px)
    statistic    median or mean of the selected measures of a frame
    scope        frame   each frame uses its own SIS
                 frames  one SIS for the dataset: frames_statistic of the
                         frames' SIS, over frames with at least min_ions
                         single ions and an SIS above 0
    fallback     a frame with no SIS of its own (scope frame): none (no
                 estimate, 0 ions in the disc), fixed (fixed_value), or
                 skip (the frame is left out of the totals)
    use_excluded excluded frames still count for scope frames and for the
                 sparsest background
    decimals     round each frame's SIS to this many decimals before it is
                 used (None: not rounded), e.g. to repeat a calibration
                 quoted to 0.1
    """
    measure: str = "box"
    box: int = 11
    radius: float = 5.0
    background: str = "none"
    background_value: float = 0.0
    sparsest_frames: int = 3
    margin: float = 3.0
    positive: bool = False
    select: str = "above_median"
    isolation_px: float = 20.0
    statistic: str = "median"
    scope: str = "frame"
    frames_statistic: str = "median"
    min_ions: int = 1
    fallback: str = "none"
    fixed_value: float = 0.0
    use_excluded: bool = False
    decimals: int | None = None


@dataclass(frozen=True)
class PileupMethod:
    """One estimate of the ions in the pile-up disc, N = S / SIS.

    kind  threshold_sum  S = sum of the disc's pixels above pixel_thresh
          baseline_sum   S = sum of the disc - baseline, at least 0; the
                         baseline is a percentile of the disc sums over the
                         frames (baseline_percentile), a fixed value, or none
          corrected_sum  S = sum of the disc - the calibration's background
                         per pixel x pixels; frames with S below min_sum
                         have no blob (0 ions)
    rounding  none, or nearest (to the nearest whole ion, halves to even;
              never below 0)
    signal_decimals  round S to this many decimals first (None: not rounded)
    """
    name: str = "threshold sum"
    kind: str = "threshold_sum"
    pixel_thresh: float = 10.0
    baseline: str = "percentile"
    baseline_percentile: float = 30.0
    baseline_value: float = 0.0
    min_sum: float = 0.0
    rounding: str = "nearest"
    signal_decimals: int | None = None
    calibration: CalibrationParams = field(default_factory=CalibrationParams)


@dataclass(frozen=True)
class AggregateParams:
    """How frames add up: sum (every frame used) or active (only frames
    whose total is above active_threshold)."""
    rule: str = "sum"
    active_threshold: float = 5.0


@dataclass(frozen=True)
class IonParams:
    """All settings of one analysis. grey: how a colour frame becomes grey,
    exact (0.299 R + 0.587 G + 0.114 B, not rounded) or rounded_8bit (the
    same weights rounded to whole counts, as most video tools do)."""
    grey: str = "exact"
    background: BackgroundParams = field(default_factory=BackgroundParams)
    region: RegionParams = field(default_factory=RegionParams)
    singles: SinglesParams = field(default_factory=SinglesParams)
    methods: tuple = ()
    aggregate: AggregateParams = field(default_factory=AggregateParams)
    name: str = ""

    def with_(self, **kw):
        return dataclasses.replace(self, **kw)

    # ── JSON ────────────────────────────────────────────────────────────
    def to_dict(self):
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d):
        return _build(cls, d)

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text):
        return cls.from_dict(json.loads(text))

    def check(self):
        """Raise ValueError naming the first setting that is not allowed."""
        allowed = [("grey", self.grey, GREY_RULES),
                   ("background.mode", self.background.mode, BACKGROUND_MODES),
                   ("region.kind", self.region.kind, REGIONS),
                   ("singles.ties", self.singles.ties, TIES),
                   ("aggregate.rule", self.aggregate.rule, AGGREGATE_RULES)]
        for m in self.methods:
            c = m.calibration
            allowed += [(f"{m.name}: kind", m.kind, PILEUP_KINDS),
                        (f"{m.name}: baseline", m.baseline, BASELINES),
                        (f"{m.name}: rounding", m.rounding, ROUNDINGS),
                        (f"{m.name}: measure", c.measure, MEASURES),
                        (f"{m.name}: background", c.background,
                         SIGNAL_BACKGROUNDS),
                        (f"{m.name}: select", c.select, SELECTIONS),
                        (f"{m.name}: statistic", c.statistic, STATISTICS),
                        (f"{m.name}: scope", c.scope, SCOPES),
                        (f"{m.name}: frames statistic", c.frames_statistic,
                         STATISTICS),
                        (f"{m.name}: fallback", c.fallback, FALLBACKS)]
        for what, value, ok in allowed:
            if value not in ok:
                raise ValueError(f"{what} is {value!r}; it can be "
                                 + ", ".join(ok))
        if self.singles.box % 2 == 0 or self.singles.local % 2 == 0:
            raise ValueError("box and local sizes must be odd")
        for m in self.methods:
            if m.calibration.measure == "box" and m.calibration.box % 2 == 0:
                raise ValueError(f"{m.name}: the calibration box must be odd")
        names = [m.name for m in self.methods]
        if len(set(names)) != len(names):
            raise ValueError("two methods have the same name")
        return self


def _build(cls, d):
    """A dataclass from a dict, nested ones too; unknown keys are an error
    (a typo in a saved file should not pass silently), missing ones take
    their default."""
    known = {f.name: f for f in fields(cls)}
    extra = set(d) - set(known)
    if extra:
        raise ValueError(f"unknown settings for {cls.__name__}: "
                         + ", ".join(sorted(extra)))
    kw = {}
    for name, value in d.items():
        sub = _NESTED.get((cls, name))
        if sub is tuple:
            kw[name] = tuple(_build(PileupMethod, v) for v in value)
        elif sub is not None:
            kw[name] = _build(sub, value)
        else:
            kw[name] = value
    return cls(**kw)


_NESTED = {
    (IonParams, "background"): BackgroundParams,
    (IonParams, "region"): RegionParams,
    (IonParams, "singles"): SinglesParams,
    (IonParams, "methods"): tuple,
    (IonParams, "aggregate"): AggregateParams,
    (PileupMethod, "calibration"): CalibrationParams,
}
