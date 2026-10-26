"""
The error table of a dataset: named error components that the user adds,
each one statistical or systematic, combined as the user chooses. Nothing
is added by default: an empty table gives no error.

Component kinds (N is the dataset's count with the table's method):

    poisson       sqrt(N)
    method_spread how far the counting methods disagree: the sample standard
                  deviation (spread "std") or half the difference between the
                  largest and smallest ("half_range") of the totals of the
                  chosen methods (all of them if none is chosen)
    fraction      fraction x N
    absolute      value, typed in
    per_frame     an error for every frame used, summed in quadrature:
                  per_frame poisson (sqrt of the frame's count), fraction
                  (fraction x the frame's count) or method_spread (as above,
                  between the methods' counts of that frame)

The statistical components are combined into one statistical error, the
systematic ones into one systematic error, and those two into the total,
in quadrature (combine "quadrature", the default) or by adding them
("linear").
"""

import json
import math
from dataclasses import asdict, dataclass, field

import numpy as np

KINDS = ("poisson", "method_spread", "fraction", "absolute", "per_frame")
GROUPS = ("statistical", "systematic")
SPREADS = ("std", "half_range")
PER_FRAME = ("poisson", "fraction", "method_spread")
COMBINE = ("quadrature", "linear")


@dataclass(frozen=True)
class ErrorComponent:
    name: str
    kind: str = "poisson"
    group: str = "statistical"
    fraction: float = 0.0
    value: float = 0.0
    methods: tuple = ()
    spread: str = "std"
    per_frame: str = "poisson"

    def check(self):
        for what, v, ok in (("kind", self.kind, KINDS),
                            ("group", self.group, GROUPS),
                            ("spread", self.spread, SPREADS),
                            ("per_frame", self.per_frame, PER_FRAME)):
            if v not in ok:
                raise ValueError(f"{self.name}: {what} is {v!r}; it can be "
                                 + ", ".join(ok))
        return self


@dataclass(frozen=True)
class ErrorTable:
    """method: whose count the errors are for ("" for the first method, or
    single ions when there is no pile-up method)."""
    components: tuple = ()
    method: str = ""
    combine: str = "quadrature"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["components"] = tuple(ErrorComponent(**{**c, "methods":
                                                   tuple(c.get("methods", ()))})
                                for c in d.get("components", ()))
        return cls(**d)

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)

    def check(self):
        if self.combine not in COMBINE:
            raise ValueError(f"combine is {self.combine!r}; it can be "
                             + ", ".join(COMBINE))
        names = [c.name for c in self.components]
        if len(set(names)) != len(names):
            raise ValueError("two error components have the same name")
        for c in self.components:
            c.check()
        return self


@dataclass
class ErrorValues:
    """The error table evaluated for one result."""
    count: float
    method: str
    components: list = field(default_factory=list)   # (name, group, value)
    statistical: float = 0.0
    systematic: float = 0.0
    total: float = 0.0


def _spread(values, how):
    values = np.asarray(values, float)
    if len(values) < 2:
        return 0.0
    if how == "std":
        return float(np.std(values, ddof=1))
    return float((values.max() - values.min()) / 2)


def _combine(values, how):
    if how == "linear":
        return float(sum(values))
    return float(math.sqrt(sum(v * v for v in values)))


def method_of(table, result):
    names = result.method_names()
    if table.method and table.method not in names:
        raise ValueError(f"no method {table.method!r} in this result; it has "
                         + ", ".join(names))
    return table.method or names[0]


def component_value(c, result, method):
    """The size of one component for a result (an aggregate count N)."""
    from .aggregate import frame_total
    n = result.totals[method].count
    names = list(c.methods) or result.method_names()
    if c.kind == "poisson":
        return math.sqrt(max(n, 0.0))
    if c.kind == "fraction":
        return c.fraction * n
    if c.kind == "absolute":
        return float(c.value)
    if c.kind == "method_spread":
        return _spread([result.totals[m].count for m in names], c.spread)
    # per_frame: the frames that went into the count
    sq = 0.0
    for row in result.rows:
        if not row.used(method) or not _counted(result, row, method):
            continue
        nf = frame_total(row, method)
        if c.per_frame == "poisson":
            e = math.sqrt(max(nf, 0.0))
        elif c.per_frame == "fraction":
            e = c.fraction * nf
        else:
            e = _spread([frame_total(row, m) for m in names], c.spread)
        sq += e * e
    return math.sqrt(sq)


def _counted(result, row, method):
    """Whether the aggregation rule let this frame into the count."""
    from .aggregate import frame_total
    agg = result.params.aggregate
    return agg.rule != "active" or frame_total(row, method) > agg.active_threshold


def evaluate(table, result):
    """-> ErrorValues of table for result (run.IonResult)."""
    table.check()
    method = method_of(table, result)
    out = ErrorValues(result.totals[method].count, method)
    for c in table.components:
        out.components.append((c.name, c.group,
                               component_value(c, result, method)))
    stat = [v for _, g, v in out.components if g == "statistical"]
    sys_ = [v for _, g, v in out.components if g == "systematic"]
    out.statistical = _combine(stat, table.combine)
    out.systematic = _combine(sys_, table.combine)
    out.total = _combine([out.statistical, out.systematic], table.combine)
    return out
