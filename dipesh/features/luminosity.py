"""Luminosity: the light inside the aperture, residual background removed."""


def luminosity(ap):
    """Sum of the aperture pixels minus bg_res per pixel."""
    return float(ap.sub[ap.mask].sum() - ap.bg_res * ap.mask.sum())
