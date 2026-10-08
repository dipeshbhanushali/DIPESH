"""detect(): planted spots are found, once each, and nothing else."""
import numpy as np

from dipesh import DetectionParams, detect


def test_finds_every_planted_spot(frame):
    img, pts = frame(7)
    spots, info = detect(img)
    assert len(spots) == len(pts)
    for s in spots:
        assert min(np.hypot(s.x - x, s.y - y) for x, y in pts) <= 2


def test_empty_frame_has_no_spots(frame):
    assert detect(frame(0)[0])[0] == []


def test_raising_the_threshold_never_adds_spots(frame):
    img, _ = frame(7)
    assert (len(detect(img, DetectionParams(abs_thresh=250))[0])
            <= len(detect(img, DetectionParams(abs_thresh=100))[0]))


def test_photometry_does_not_change_the_count(frame):
    img, _ = frame(7)
    a, _ = detect(img, photometry=False)
    b, _ = detect(img, photometry=True)
    assert [s.as_tuple() for s in a] == [s.as_tuple() for s in b]


def two_spots(gaussian_spot, distance):
    """Two equal spots `distance` px apart on a flat background."""
    a, (cx, cy) = gaussian_spot(200, 2.0, size=257, offset=10.0)
    b, _ = gaussian_spot(200, 2.0, size=257, centre=(cx + distance, cy))
    return a + b


def test_two_peaks_closer_than_min_dist_are_one_particle(gaussian_spot):
    """Peaks 8 px apart with min_dist = 12 -> count 1; with min_dist = 6 -> 2."""
    img = two_spots(gaussian_spot, 8)
    assert len(detect(img, DetectionParams(min_dist=12))[0]) == 1
    assert len(detect(img, DetectionParams(min_dist=6))[0]) == 2


def test_two_peaks_further_than_min_dist_are_two_particles(gaussian_spot):
    """Peaks 20 px apart with min_dist = 12 -> count 2."""
    assert len(detect(two_spots(gaussian_spot, 20))[0]) == 2


def test_a_flat_topped_spot_is_counted_once(gaussian_spot):
    """A saturated spot has several pixels at the maximum; NMS keeps one."""
    img, _ = gaussian_spot(600, 3.0, size=257, offset=10.0)
    img = np.clip(img, 0, 255)
    assert (img == 255).sum() > 20
    assert len(detect(img)[0]) == 1


def test_the_adaptive_threshold_is_the_larger_of_the_two(frame):
    """thresh = max(abs_thresh, n_sigma * noise); abs_thresh alone when
    adaptive is off."""
    img, _ = frame(3)
    _, info = detect(img, DetectionParams(abs_thresh=1.0, n_sigma=10.0))
    assert info.thresh == 10.0 * info.sigma > 1.0
    _, info = detect(img, DetectionParams(abs_thresh=1.0, adaptive=False))
    assert info.thresh == 1.0
