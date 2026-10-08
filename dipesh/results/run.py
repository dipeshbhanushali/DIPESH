"""
One analysed run: the spots of its image, the image-level numbers, its
Batman parameters and its pickup measurements.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from ..single_image_analysis import (DetectionParams, DetectionInfo, Item,
                                     detect, load_image, parse_batman)


@dataclass
class RunResult:
    item: Item
    spots: list = field(default_factory=list)
    info: DetectionInfo | None = None
    batman: dict = field(default_factory=dict)
    pickup: dict = field(default_factory=dict)   # flat pickup columns
    error: str | None = None

    @property
    def ok(self):
        return self.error is None

    @property
    def n(self):
        return len(self.spots)

    def metric(self, name):
        """A per-run number by name, for the plot view."""
        i = self.info
        isol = [s for s in self.spots if s.is_isolated]
        lums = [s.luminosity for s in self.spots if math.isfinite(s.luminosity)]
        table = {
            "pbar_count": float(self.n),
            "pbar_count_lum": i.pbar_count_lum if i else float("nan"),
            "integrated_lum": i.integrated_lum if i else float("nan"),
            "mean_spot_luminosity": float(np.mean(lums)) if lums else float("nan"),
            "n_isolated": float(len(isol)),
            "noise_sigma": i.sigma if i else float("nan"),
            "run_number": float(self.item.run_number),
        }
        if name in table:
            return table[name]
        if name in self.pickup:
            try:
                return float(self.pickup[name])
            except (TypeError, ValueError):
                return float("nan")
        if name in self.batman:
            return float(self.batman[name])
        return float("nan")


RUN_METRICS = {
    "pbar_count":           "Antiproton count",
    "pbar_count_lum":       "Count from luminosity",
    "integrated_lum":       "Integrated luminosity",
    "mean_spot_luminosity": "Mean spot luminosity",
    "n_isolated":           "Isolated spots",
    "noise_sigma":          "Image noise σ",
}


def analyse(item: Item, params: DetectionParams) -> RunResult:
    """Detect and measure every spot in one image, and read its Batman."""
    img = load_image(item.path)
    if img is None:
        return RunResult(item, error="could not read image")
    spots, info = detect(img, params, photometry=True)
    return RunResult(item, spots, info, parse_batman(item.folder))
