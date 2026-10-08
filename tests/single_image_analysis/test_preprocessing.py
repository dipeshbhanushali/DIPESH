"""Hot pixels, bit-depth scaling and the masked background."""
import cv2
import numpy as np
import pytest

from dipesh import DetectionParams, detect, prepare, to_float
from dipesh.single_image_analysis import (masked_background,
                                                       remove_hot_pixels)


# ── hot pixels ──────────────────────────────────────────────────────────────
def test_hot_pixels_are_removed_not_counted(frame):
    img, pts = frame(3, hot=4)
    spots, info = detect(img)
    assert info.hot_pixels >= 4 and len(spots) == len(pts)


def test_a_hot_pixel_is_replaced_by_its_3x3_median():
    """A pixel more than hotpix_delta above the median of its 3x3
    neighbourhood takes that median."""
    img = np.full((32, 32), 20.0, np.float32)
    img[10, 12] = 200.0
    out, n = remove_hot_pixels(img, DetectionParams(hotpix_delta=60))
    assert n == 1 and out[10, 12] == 20.0
    assert img[10, 12] == 200.0                     # the input is not touched


def test_hot_pixel_delta_zero_switches_the_correction_off():
    img = np.full((32, 32), 20.0, np.float32)
    img[10, 12] = 200.0
    out, n = remove_hot_pixels(img, DetectionParams(hotpix_delta=0))
    assert n == 0 and out[10, 12] == 200.0


def test_the_peak_of_a_real_spot_is_not_a_hot_pixel(gaussian_spot):
    """A spot of sigma 1.5 px: the peak is 22 % above its neighbours, far
    less than hotpix_delta."""
    img, (cx, cy) = gaussian_spot(200, 1.5, offset=10.0)
    out, n = remove_hot_pixels(img, DetectionParams())
    assert n == 0 and out[cy, cx] == img[cy, cx]


def test_hot_pixel_delta_scales_with_the_bit_depth():
    """On a 12-bit image the same delta means 60 * 4095 / 255 counts."""
    img = np.full((32, 32), 300.0, np.float32)
    img[5, 5] = 300.0 + 500.0                       # below 60 * 16.06 = 963
    img[20, 20] = 4000.0                            # sets the scale, and is hot
    out, n = remove_hot_pixels(img, DetectionParams(hotpix_delta=60))
    assert n == 1 and out[5, 5] == 800.0 and out[20, 20] == 300.0


# ── bit depth ───────────────────────────────────────────────────────────────
def test_normalisation_is_by_bit_depth_not_content(frame):
    img8, _ = frame(4)
    img12 = (img8 * 4095.0 / 255.0).astype(np.float32)
    assert np.allclose(to_float(img8), to_float(img12), atol=1e-3)


@pytest.mark.parametrize("peak, full_scale", [(200, 255), (255, 255),
                                              (256, 1023), (1023, 1023),
                                              (1024, 4095), (4095, 4095),
                                              (4096, 65535), (65535, 65535)])
def test_the_full_scale_is_the_smallest_bit_depth_that_holds_the_maximum(
        peak, full_scale):
    """out = in * 255 / full_scale, full_scale in (255, 1023, 4095, 65535)."""
    img = np.array([[0.0, peak / 2, peak]], np.float32)
    out = to_float(img)
    assert out[0, 2] == pytest.approx(peak * 255.0 / full_scale, rel=1e-6)
    assert out[0, 1] == pytest.approx(out[0, 2] / 2, rel=1e-6)


def test_an_8_bit_image_is_not_rescaled():
    img = np.array([[3.0, 40.0, 180.0]], np.float32)
    assert np.array_equal(to_float(img), img)


# ── background ──────────────────────────────────────────────────────────────
def test_the_masked_background_does_not_rise_under_a_bright_spot(
        gaussian_spot):
    """A plain 51 px blur lifts the baseline under a spot of A = 200,
    sigma = 2.2 by more than 5 counts; the masked second pass stays within
    one count of the true offset (only the faint tail below the mask level
    still leaks in)."""
    offset = 10.0
    img, (cx, cy) = gaussian_spot(200, 2.2, size=257, offset=offset)
    plain = cv2.GaussianBlur(img, (51, 51), 0)
    bg, _ = masked_background(img, DetectionParams())
    assert plain[cy, cx] - offset > 5.0
    assert abs(bg[cy, cx] - offset) < 1.0


def test_a_flat_image_has_itself_as_background():
    img = np.full((128, 128), 17.0, np.float32)
    bg, sigma = masked_background(img, DetectionParams())
    assert np.allclose(bg, 17.0, atol=1e-3) and sigma == 1e-3


def test_the_noise_estimate_is_the_gaussian_sigma():
    """sigma = 1.4826 * MAD recovers the sigma of Gaussian noise (2 %)."""
    rng = np.random.default_rng(0)
    img = rng.normal(50, 3.0, (512, 512)).astype(np.float32)
    assert masked_background(img, DetectionParams())[1] == pytest.approx(3.0, rel=0.02)


def test_prepare_returns_a_non_negative_image_on_the_0_255_scale(frame):
    img, _ = frame(4)
    diff, sigma, n_hot = prepare(img * 16.0)        # a 12-bit frame
    assert diff.min() >= 0 and 150 < diff.max() <= 255 and sigma > 0
