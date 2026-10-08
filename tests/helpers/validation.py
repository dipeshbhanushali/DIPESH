"""
Validation of every spot feature against a value known in closed form.

Each function returns a list of Case(label, true, measured, tolerance). The
tests in tests/features/ assert them; report/make_report.py prints them.

The spots are noise-free Gaussians centred on a pixel, on a zero background.
Unless a case is about the plateau, the aperture is WIDE: it is allowed to
grow to 6 sigma and never stops early, so it does not cut the spot (the light
outside 6 sigma is exp(-18) = 1.5e-8 of the total). Sampling a Gaussian of
sigma >= 1.5 px on the pixel grid changes its sums by less than 1e-15, so what
is left is float32 rounding in the image, about 1e-6.
"""
import math
from dataclasses import dataclass

import numpy as np

from dipesh import DetectionParams, detect
from dipesh.features import (area, concentration, eccentricity,
                                          grow, luminosity, profile_slope,
                                          radial_sigma)

from synthetic import gaussian_spot

SIGMAS = (1.5, 2.0, 3.0)
AMP = 100.0


@dataclass
class Case:
    label: str
    true: float
    measured: float
    tol: float                   # relative; absolute when the true value is 0
    absolute: bool = False       # tol and error in the units of the value

    @property
    def error(self):
        d = abs(self.measured - self.true)
        return d if self.absolute or not self.true else d / abs(self.true)

    @property
    def ok(self):
        return self.error <= self.tol


def wide(sigma):
    """Settings whose aperture does not cut a spot of this sigma."""
    return DetectionParams(spot_max_radius=math.ceil(6 * sigma),
                           plateau_frac=0.0)


def aperture(amp=AMP, sx=2.0, sy=None, angle_deg=0.0, params=None,
             shift=(0.0, 0.0)):
    """The Aperture of one synthetic spot. shift moves the centre of the
    Gaussian off the pixel the aperture is grown on, by (dx, dy) px."""
    size = 129
    c = size // 2
    img, _ = gaussian_spot(amp, sx, sy, angle_deg, size,
                           (c + shift[0], c + shift[1]))
    return grow(img, c, c, 0.0, params or wide(max(sx, sy or sx)))


# ── luminosity ──────────────────────────────────────────────────────────────
def luminosity_cases():
    """L = 2 pi A sigma^2."""
    return [Case(f"sigma = {s:g} px", 2 * math.pi * AMP * s * s,
                 luminosity(aperture(sx=s)), 1e-4) for s in SIGMAS]


def plateau_luminosity_cases():
    """With the default plateau rule the aperture stops at radius R where a
    ring adds < 2 %; the light inside is 2 pi A sigma^2 (1 - exp(-R^2 / 2 sigma^2)),
    at most a few per cent below the total."""
    out = []
    for s in SIGMAS:
        ap = aperture(sx=s, params=DetectionParams(spot_max_radius=30))
        total = 2 * math.pi * AMP * s * s
        out.append(Case(f"sigma = {s:g} px, R = {ap.r_used} px",
                        total, luminosity(ap), 0.03))
    return out


# ── radial sigma ────────────────────────────────────────────────────────────
def radial_sigma_cases():
    """sqrt(<r^2>) = sqrt(2) sigma for a round 2-D Gaussian."""
    return [Case(f"sigma = {s:g} px", math.sqrt(2) * s,
                 radial_sigma(aperture(sx=s)), 1e-3) for s in SIGMAS]


# ── concentration ───────────────────────────────────────────────────────────
# The spot is centred 0.3 px right and 0.2 px down of a pixel, as a real spot
# would be. Centred exactly on a pixel, four pixels sit at exactly r = 2 and
# the 1e-7 rounding of the centroid decides which of them count: the value
# then moves by about 10 % (see concentration_on_pixel_cases).
SHIFT = (0.3, 0.2)


def pixels_within_2px(sigma, centre):
    """Fraction of a unit Gaussian's light on the pixels within 2 px of its
    centre, summed pixel by pixel."""
    cx, cy = centre
    tot = 0.0
    for iy in range(-4, 5):
        for ix in range(-4, 5):
            q = (ix - cx) ** 2 + (iy - cy) ** 2
            if q <= 4:
                tot += math.exp(-q / (2 * sigma * sigma))
    return tot / (2 * math.pi * sigma * sigma)


def concentration_cases():
    """Light within 2 px: 1 - exp(-4 / (2 sigma^2)) for a continuous Gaussian.
    The code sums whole pixels whose centre is within 2 px of the centroid:
    13 pixels for this spot, where the disc has an area of 4 pi = 12.6 px, so
    it reads about 3 % high. Tolerance 5 %."""
    return [Case(f"sigma = {s:g} px", 1 - math.exp(-4 / (2 * s * s)),
                 concentration(aperture(sx=s, shift=SHIFT)), 0.05)
            for s in SIGMAS]


def concentration_pixel_cases():
    """The same on the pixel grid, exactly: sum of exp(-r^2 / 2 sigma^2) over
    the pixels with r <= 2 px from the centre, over 2 pi sigma^2."""
    return [Case(f"sigma = {s:g} px", pixels_within_2px(s, SHIFT),
                 concentration(aperture(sx=s, shift=SHIFT)), 1e-4)
            for s in SIGMAS]


def concentration_on_pixel_cases():
    """A spot centred exactly on a pixel: 13 pixels have r <= 2, four of them
    at exactly r = 2. Rounding of the centroid drops some of those four."""
    return [Case(f"sigma = {s:g} px", pixels_within_2px(s, (0.0, 0.0)),
                 concentration(aperture(sx=s)), 0.15) for s in SIGMAS]


# ── eccentricity ────────────────────────────────────────────────────────────
ELLIPSES = ((3.0, 2.0), (3.0, 1.5), (4.0, 2.0))


def eccentricity_cases():
    """e = sqrt(1 - sigma_y^2 / sigma_x^2); 0 for a round spot."""
    out = [Case(f"round, sigma = {s:g} px", 0.0,
                eccentricity(aperture(sx=s)), 0.01) for s in SIGMAS]
    for sx, sy in ELLIPSES:
        out.append(Case(f"sigma_x = {sx:g}, sigma_y = {sy:g} px",
                        math.sqrt(1 - sy * sy / (sx * sx)),
                        eccentricity(aperture(sx=sx, sy=sy)), 1e-3))
    return out


def eccentricity_rotation_cases():
    """Turning the spot by 45 degrees does not change e."""
    out = []
    for sx, sy in ELLIPSES:
        out.append(Case(f"sigma_x = {sx:g}, sigma_y = {sy:g} px, at 45 deg",
                        math.sqrt(1 - sy * sy / (sx * sx)),
                        eccentricity(aperture(sx=sx, sy=sy, angle_deg=45)),
                        1e-3))
    return out


# ── area and aperture ───────────────────────────────────────────────────────
def area_cases():
    """Area = number of pixels with r^2 <= R^2, R the radius used."""
    out = []
    for s in SIGMAS:
        ap = aperture(sx=s, params=DetectionParams())
        R = ap.r_used
        yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
        out.append(Case(f"sigma = {s:g} px, R = {R} px",
                        float((xx * xx + yy * yy <= R * R).sum()),
                        float(area(ap)), 0.0))
    return out


def radius_for(sigma, **kw):
    return aperture(sx=sigma, params=DetectionParams(**kw)).r_used


def plateau_radius(sigma, frac=0.02, r_max=12):
    """The radius the plateau rule gives for a continuous round Gaussian:
    the first R whose ring adds less than frac of the light inside R - 1."""
    inside = lambda r: 1 - math.exp(-r * r / (2 * sigma * sigma))
    for r in range(2, r_max + 1):
        if inside(r) - inside(r - 1) < frac * inside(r - 1):
            return r
    return r_max


def aperture_radius_cases():
    """R = first radius whose ring adds < plateau_frac of the light inside,
    capped at spot_max_radius. The prediction is for a continuous Gaussian;
    on pixels the ring sums differ a little, so R may be 1 px off."""
    return [Case(f"sigma = {s:g} px", float(plateau_radius(s)),
                 float(radius_for(s)), 1.0, absolute=True)
            for s in SIGMAS + (6.0,)]


# ── profile slope ───────────────────────────────────────────────────────────
def slope_for(sigma, amp=AMP):
    return profile_slope(aperture(amp=amp, sx=sigma, params=DetectionParams()))


def profile_slope_values():
    """[(sigma, slope)] with the default settings."""
    return [(s, slope_for(s)) for s in SIGMAS]


# ── brightness independence ─────────────────────────────────────────────────
def brightness_cases(factor=3.0):
    """Concentration, eccentricity and profile slope of the same spot, made
    `factor` times brighter: unchanged."""
    out = []
    for name, f in (("concentration", concentration),
                    ("eccentricity", eccentricity),
                    ("profile slope", profile_slope)):
        p = DetectionParams()
        a = f(aperture(amp=60.0, sx=3.0, sy=2.0, params=p))
        b = f(aperture(amp=60.0 * factor, sx=3.0, sy=2.0, params=p))
        out.append(Case(f"{name}, amplitude x {factor:g}", a, b, 1e-4))
    return out


# ── the whole pipeline ──────────────────────────────────────────────────────
def pipeline_spot(sigma, amp=200.0, offset=10.0):
    """The one spot detect() finds in a frame with a flat offset."""
    img, _ = gaussian_spot(amp, sigma, size=257, offset=offset)
    spots, _ = detect(img, DetectionParams(), photometry=True)
    assert len(spots) == 1, len(spots)
    return spots[0]


def pipeline_luminosity_cases():
    """Through detect() with the default settings: L within 7 % of
    2 pi A sigma^2. The loss grows with sigma: the plateau rule cuts the tail
    and the 51 px background kernel takes a little of a broad spot."""
    out = []
    for s in SIGMAS:
        sp = pipeline_spot(s)
        out.append(Case(f"sigma = {s:g} px, R = {sp.radius_used} px",
                        2 * math.pi * 200.0 * s * s, sp.luminosity, 0.07))
    return out
