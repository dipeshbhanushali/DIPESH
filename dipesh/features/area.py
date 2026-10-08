"""Area: the number of pixels in the aperture."""


def area(ap):
    """Pixels with r^2 <= r_used^2 (fewer at the image edge)."""
    return int(ap.mask.sum())
