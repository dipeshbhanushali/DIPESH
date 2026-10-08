"""Concentration: the fraction of the light within 2 px of the centroid.
Does not depend on the brightness."""


def concentration(ap):
    """sum(w where r <= 2 px) / sum(w)."""
    w, dx, dy = ap.w, ap.dx, ap.dy
    core = w[(dx * dx + dy * dy) <= 4]
    return float(core.sum() / ap.wsum)
