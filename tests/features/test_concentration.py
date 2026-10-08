"""Concentration: the fraction of the light within 2 px of the centroid."""
import pytest

import validation as v


@pytest.mark.parametrize("case", v.concentration_cases(), ids=lambda c: c.label)
def test_concentration_of_a_gaussian_is_1_minus_exp(case):
    """C = 1 - exp(-4 / (2 sigma^2)). Tolerance 5 %: whole pixels, not a disc."""
    assert case.ok, case
    assert case.measured > case.true                 # 13 px > 4 pi px


@pytest.mark.parametrize("case", v.concentration_pixel_cases(), ids=lambda c: c.label)
def test_concentration_equals_the_sum_over_the_pixels_within_2px(case):
    """C = sum over pixels with r <= 2 of exp(-r^2 / 2 sigma^2) / (2 pi sigma^2); tolerance 1e-4."""
    assert case.ok, case


@pytest.mark.parametrize("case", v.concentration_on_pixel_cases(), ids=lambda c: c.label)
def test_concentration_of_a_spot_centred_on_a_pixel_is_within_15_percent(case):
    """Same sum with the centre on a pixel: four pixels lie at exactly r = 2 and rounding decides; tolerance 15 %."""
    assert case.ok, case


def test_a_narrower_spot_is_more_concentrated():
    """C decreases with sigma."""
    c = [x.measured for x in v.concentration_cases()]
    assert c == sorted(c, reverse=True)
