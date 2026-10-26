"""
The per-frame table and the totals over the frames used.

Every frame has the single ions counted in the region, and for every
pile-up method its SIS, the disc light S it counted, the estimated ions in
the disc and the frame's total (single ions + disc). Excluded frames stay
in the table, marked, and are left out of every total.
"""

from dataclasses import dataclass, field

SINGLES_ONLY = "single ions"       # the total when there is no pile-up method


@dataclass
class MethodFrame:
    sis: float | None = None       # single-ion signal used for this frame
    sis_ions: int = 0              # ions it was measured on (scope frame)
    signal: float = 0.0            # S, the disc light counted
    inner: float = 0               # estimated ions in the pile-up disc
    total: float = 0               # single ions + inner
    skipped: bool = False          # no SIS and fallback "skip"


@dataclass
class FrameRow:
    frame: int
    singles: int
    excluded: bool = False
    disc_sum: float = 0.0          # all the light in the disc
    methods: dict = field(default_factory=dict)        # name -> MethodFrame

    def used(self, method):
        if self.excluded:
            return False
        m = self.methods.get(method)
        return not (m is not None and m.skipped)


@dataclass
class Total:
    count: float                   # the total of the dataset
    singles: int                   # of which single ions
    inner: float                   # of which estimated in the pile-up disc
    frames: int                    # frames that went into it


def frame_total(row, method):
    return row.methods[method].total if method in row.methods else row.singles


def totals(rows, methods, aggregate):
    """{method: Total} over the frames used. methods: names, or none for
    single ions only. aggregate: params.AggregateParams (sum: every frame
    used; active: only frames whose total is above active_threshold)."""
    out = {}
    for name in (methods or [SINGLES_ONLY]):
        use = [r for r in rows if r.used(name)]
        if aggregate.rule == "active":
            use = [r for r in use
                   if frame_total(r, name) > aggregate.active_threshold]
        singles = sum(r.singles for r in use)
        inner = sum(r.methods[name].inner for r in use if name in r.methods)
        out[name] = Total(singles + inner, singles, inner, len(use))
    return out
