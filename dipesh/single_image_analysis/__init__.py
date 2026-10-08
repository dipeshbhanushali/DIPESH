"""
Single-image analysis: from one camera image to a list of spots.

    params          DetectionParams, Spot, DetectionInfo
    loading         scan, load_image, parse_batman
    preprocessing   hot pixels, bit-depth scaling, background
    detection       detect()
    image_luminosity  integrated light on the MCP, count from light
"""

from .params import (DetectionParams, DEFAULT_PARAMS, Spot, DetectionInfo,
                     SPOT_FEATURES)
from .loading import (IMAGE_EXTS, RUN_PATTERN, Item, scan, find_run_folders,
                      find_tiff, load_image, parse_batman)
from .preprocessing import (to_float, remove_hot_pixels, masked_background,
                            prepare)
from .image_luminosity import image_luminosity
from .detection import detect
