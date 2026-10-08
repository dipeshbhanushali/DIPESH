"""Integrated light inside the MCP circle and the count derived from it."""
import numpy as np
import pytest

from dipesh import DetectionInfo, DetectionParams, Spot
from dipesh.single_image_analysis import image_luminosity


def measure(diff, spots, **kw):
    info = DetectionInfo(sigma=1.0, thresh=1.0, hot_pixels=0)
    image_luminosity(diff, spots, info, DetectionParams(**kw))
    return info


def spots_image(gaussian_spot, centres, amp=100.0, sigma=1.2, floor=0.0):
    img = np.full((201, 201), floor, np.float32)
    for c in centres:
        img += gaussian_spot(amp, sigma, size=201, centre=c)[0]
    return img, [Spot(x, y, amp, 0.0) for x, y in centres]


def test_integrated_light_is_the_sum_of_the_spots(gaussian_spot):
    """Three spots of 2 pi A sigma^2 each inside the circle -> 3 x that."""
    centres = [(60, 60), (100, 120), (140, 80)]
    diff, spots = spots_image(gaussian_spot, centres)
    info = measure(diff, spots, mcp_region=(100, 100, 90))
    one = 2 * np.pi * 100.0 * 1.2 ** 2
    assert info.integrated_lum == pytest.approx(3 * one, rel=1e-3)
    assert info.aperture_lum == pytest.approx(3 * one, rel=1e-3)


def test_the_count_from_light_is_the_number_of_equal_spots(gaussian_spot):
    """count = integrated light / mean aperture light per spot."""
    centres = [(60, 60), (100, 120), (140, 80), (90, 60)]
    diff, spots = spots_image(gaussian_spot, centres)
    info = measure(diff, spots, mcp_region=(100, 100, 90))
    assert info.pbar_count_lum == pytest.approx(4.0, rel=1e-3)


def test_a_flat_residual_floor_is_removed_from_the_light(gaussian_spot):
    """The mean of the spot-free pixels is subtracted per pixel, so a floor
    of 0.7 counts changes nothing."""
    centres = [(60, 60), (140, 80)]
    a = measure(*spots_image(gaussian_spot, centres), mcp_region=(100, 100, 90))
    b = measure(*spots_image(gaussian_spot, centres, floor=0.7),
                mcp_region=(100, 100, 90))
    assert b.bg_residual == pytest.approx(0.7, abs=1e-3)
    assert b.integrated_lum == pytest.approx(a.integrated_lum, rel=1e-3)
    assert b.pbar_count_lum == pytest.approx(a.pbar_count_lum, rel=1e-3)


def test_light_outside_the_mcp_circle_is_not_integrated(gaussian_spot):
    """One spot inside the circle and one outside: only the first counts."""
    diff, spots = spots_image(gaussian_spot, [(100, 100), (180, 180)])
    inside = measure(diff, spots[:1], mcp_region=(100, 100, 40))
    assert inside.integrated_lum == pytest.approx(2 * np.pi * 100 * 1.44, rel=1e-3)
    whole = measure(diff, spots, mcp_region=None)
    assert whole.integrated_lum == pytest.approx(2 * inside.integrated_lum, rel=1e-3)


def test_no_spots_gives_a_count_of_zero():
    info = measure(np.zeros((64, 64), np.float32), [], mcp_region=None)
    assert info.pbar_count_lum == 0.0 and info.aperture_lum == 0.0
