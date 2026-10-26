"""
Single ions: the separated hits outside the pile-up disc, counted one by
one with the same spot finder as single-image detection (find_spots).
"""

from ..single_image_analysis import find_spots
from .geometry import restrict
from .tie_order import ORDERS


def find_singles(diff, count_mask, singles):
    """The single ions in a background-subtracted frame, inside the region
    (count_mask; None for the whole frame). singles: SinglesParams.
    -> [(x, y, peak, box_sum), ...], brightest first"""
    return find_spots(restrict(diff, count_mask), singles.peak_thresh,
                      singles.box_thresh, singles.min_dist, box=singles.box,
                      local=singles.local, spread_min=singles.spread_min,
                      order=ORDERS[singles.ties])
