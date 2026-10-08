"""Area: the number of pixels in the aperture."""
import pytest

import validation as v
from dipesh import DetectionParams
from dipesh.features import area, grow


@pytest.mark.parametrize("case", v.area_cases(), ids=lambda c: c.label)
def test_area_is_the_number_of_pixels_within_the_radius_used(case):
    """area = #{pixels with r^2 <= R^2}, R the radius used; exact."""
    assert case.ok, case


def test_area_is_smaller_at_the_image_edge(gaussian_spot):
    """Half the aperture is off the image: fewer pixels than the full disc."""
    inside, (cx, cy) = gaussian_spot(100, 2.0)
    edge, _ = gaussian_spot(100, 2.0, centre=(0, cy))
    p = DetectionParams(plateau_frac=0.0, spot_max_radius=6)
    full = area(grow(inside, cx, cy, 0.0, p))
    assert full == 113
    assert area(grow(edge, 0, cy, 0.0, p)) == (full + 13) // 2    # 13 on the axis
