"""The learn lessons show the analysis's own numbers, not a copy: the image
lesson's stages give exactly detect()'s spots, and the spots lesson's
ellipse and profile come from the functions eccentricity and profile slope
are computed with. Pinned on the six reference frames."""
import json
import math
import os

import numpy as np
import pytest

from dipesh import DetectionParams, detect, load_image, to_float
from dipesh.features import (eccentricity, profile_fit, profile_slope,
                             second_moments)
from dipesh.graphical_interface.learn.crops import aperture, stages
from dipesh.single_image_analysis import suppress

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "reference")
with open(os.path.join(REF, "golden.json")) as f:
    GOLDEN = json.load(f)["frames"]
FRAMES = sorted(GOLDEN)


def frame(name):
    return to_float(load_image(os.path.join(REF, "images", name)))


@pytest.mark.parametrize("name", FRAMES)
def test_the_lesson_stages_give_exactly_the_detected_spots(name):
    p = DetectionParams()
    img = frame(name)
    st = stages(img, p)
    spots, info = detect(img, p)
    mine = suppress(st.diff, st.sum5, st.candidates, p)
    assert [(s.x, s.y, s.peak, s.sum5x5) for s in mine] == \
        [(s.x, s.y, s.peak, s.sum5x5) for s in spots]
    assert (st.sigma, st.thresh) == (info.sigma, info.thresh)
    assert len(mine) == GOLDEN[name]["count"]


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-15)


@pytest.mark.parametrize("name", FRAMES)
def test_the_spots_lesson_draws_from_the_numbers_that_are_stored(name):
    p = DetectionParams()
    img = frame(name)
    st = stages(img, p)
    spots, info = detect(img, p, photometry=True)
    want = GOLDEN[name]["spots"]
    for s, w in zip(spots, want):
        ap = aperture(st, s, info.bg_residual, p)
        lam, vec = second_moments(ap)
        assert close(eccentricity(ap), w["eccentricity"])
        r, log_w, slope, intercept = profile_fit(ap)
        assert close(slope, w["profile_slope"])
        assert slope == profile_slope(ap)
        # second_moments is a true eigen-decomposition of the covariance,
        # largest first; np.linalg.eigh gives the same, smallest first
        cov = np.array([[(ap.w * ap.dx * ap.dx).sum(),
                         (ap.w * ap.dx * ap.dy).sum()],
                        [(ap.w * ap.dx * ap.dy).sum(),
                         (ap.w * ap.dy * ap.dy).sum()]]) / ap.wsum
        assert lam[0] >= lam[1]
        assert np.allclose(np.linalg.eigh(cov)[0][::-1], lam, atol=1e-9)
        for k in range(2):
            assert np.allclose(cov @ vec[:, k], lam[k] * vec[:, k], atol=1e-9)
        if len(r) >= 3:                           # the line drawn is the fit
            assert np.allclose(np.polyfit(r, log_w, 1), [slope, intercept])
