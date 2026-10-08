"""
Settings and result records of the single-image analysis.

Defaults suit an 8- to 16-bit camera looking at an MCP / phosphor screen.
"""

from dataclasses import dataclass, asdict, replace


@dataclass(frozen=True)
class DetectionParams:
    """Everything that controls detection and spot measurement.

    Defaults suit an 8- to 16-bit camera looking at an MCP / phosphor screen.
    """
    # detection
    bg_blur_size: int = 51       # background kernel (forced odd)
    abs_thresh: float = 140.0    # peak threshold, 0-255 scale
    adaptive: bool = True        # also require n_sigma x image noise
    n_sigma: float = 10.0
    sum_thresh: float = 80.0     # minimum 5x5 summed brightness
    spread_min: float = 5.0      # minimum 5x5-sum / peak (rejects hot pixels)
    min_dist: int = 12           # two peaks closer than this are one particle
    nms_size: int = 7            # non-maximum-suppression window (forced odd)
    hotpix_delta: float = 60.0   # hot-pixel rejection strength (0 disables)
    mask_nsigma: float = 4.0     # masking level in the 2-pass background

    # spot photometry (does not change the count)
    aperture_radius: int = 5     # fixed aperture for aperture_lum
    spot_max_radius: int = 12    # grow each spot's aperture to at most this
    plateau_frac: float = 0.02   # stop growing when a ring adds < this fraction
    isolation_factor: float = 2.0  # isolated if nearest spot > this x aperture

    # MCP active area (cx, cy, r) in pixels. Used for the integrated
    # luminosity and drawn on the image; never affects the count.
    mcp_region: tuple | None = (640, 512, 430)

    def replace(self, **kw):
        return replace(self, **kw)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        names = set(cls.__dataclass_fields__)
        kw = {k: v for k, v in d.items() if k in names}
        if isinstance(kw.get("mcp_region"), list):
            kw["mcp_region"] = tuple(kw["mcp_region"])
        return cls(**kw)


DEFAULT_PARAMS = DetectionParams()


@dataclass
class Spot:
    """One detected antiproton candidate. Photometry fields are filled when
    detect(..., photometry=True)."""
    x: int
    y: int
    peak: float                  # background-subtracted peak, 0-255 scale
    sum5x5: float
    luminosity: float = float("nan")
    radius_used: int = 0
    area: int = 0
    radial_sigma: float = float("nan")
    concentration: float = float("nan")
    eccentricity: float = float("nan")
    profile_slope: float = float("nan")
    nn_dist: float = float("inf")
    is_isolated: bool = False

    def as_tuple(self):
        return (self.x, self.y, self.peak, self.sum5x5)


SPOT_FEATURES = ["luminosity", "peak", "sum5x5", "radial_sigma", "area",
                 "concentration", "eccentricity", "profile_slope", "nn_dist"]


@dataclass
class DetectionInfo:
    sigma: float                 # robust noise of the image
    thresh: float                # threshold actually applied
    hot_pixels: int
    integrated_lum: float = float("nan")   # all light inside the MCP region
    aperture_lum: float = float("nan")     # sum of fixed apertures on spots
    pbar_count_lum: float = float("nan")   # integrated / single-spot light
    bg_residual: float = float("nan")
