"""
Named settings. The "legacy" presets repeat analyses made before DIPESH had
an ion analysis, value for value (thresholds, windows, background, geometry
and calibration), so that tests can show the general code gives exactly the
same numbers. They describe particular detectors and videos; they are not
the defaults for new data, which are IonParams(). They also break ties
between equally bright candidates as NumPy 1.x did (tie_order.py), which
the earlier numbers depend on.
"""

from .params import (AggregateParams, BackgroundParams, CalibrationParams,
                     IonParams, PileupMethod, RegionParams, SinglesParams)

# a 1280 x 1024 camera: the MCP circle and the pile-up disc of the transport
# videos (centres of the bounding boxes 280-1005 x 229-872 and
# 570-670 x 480-615)
_TRANSPORT_RING = RegionParams(kind="ring", cx=642, cy=550, r=370,
                               inner_cx=620, inner_cy=547, inner_r=65)

LEGACY = {
    # every frame, no pile-up disc; background from the 100 darkest frames
    "legacy release, whole frame": IonParams(
        name="legacy release, whole frame",
        grey="rounded_8bit",
        background=BackgroundParams(mode="darkest", n=100),
        region=RegionParams(kind="frame"),
        singles=SinglesParams(peak_thresh=5, box=5, box_thresh=80,
                              min_dist=9, local=7, ties="numpy1"),
        aggregate=AggregateParams(rule="sum")),

    # single ions in a ring, the disc from its bright pixels / per-frame SIS;
    # background from a separate video
    "legacy transport, intensity": IonParams(
        name="legacy transport, intensity",
        grey="rounded_8bit",
        background=BackgroundParams(mode="video"),
        region=_TRANSPORT_RING,
        singles=SinglesParams(peak_thresh=25.5, box=7, box_thresh=110,
                              min_dist=9, local=7, ties="numpy1"),
        methods=(PileupMethod(
            name="intensity", kind="threshold_sum", pixel_thresh=10.0,
            rounding="nearest",
            calibration=CalibrationParams(
                measure="box", box=11, select="above_median",
                statistic="median", scope="frame", fallback="none")),)),

    # the same ring, the disc from its background-corrected light / one SIS
    # from round apertures over all frames
    "legacy transport, luminosity": IonParams(
        name="legacy transport, luminosity",
        grey="rounded_8bit",
        background=BackgroundParams(mode="video"),
        region=_TRANSPORT_RING,
        singles=SinglesParams(peak_thresh=25, box=7, box_thresh=100,
                              min_dist=9, local=7, ties="numpy1"),
        methods=(PileupMethod(
            name="luminosity", kind="corrected_sum", min_sum=100.0,
            rounding="none", signal_decimals=1,
            calibration=CalibrationParams(
                measure="aperture", radius=5.0, background="sparsest",
                background_value=11.5, sparsest_frames=3, margin=3.0,
                positive=True, select="all", statistic="mean",
                scope="frames", frames_statistic="median", min_ions=3,
                use_excluded=True, decimals=1)),)),

    # storage-time videos (700 x 600): single ions in a ring, the disc from
    # its light above a baseline / per-frame SIS (550 when a frame has none);
    # background from 300 frames picked at random
    "legacy storage": IonParams(
        name="legacy storage",
        grey="rounded_8bit",
        background=BackgroundParams(mode="random", n=300, seed=42),
        region=RegionParams(kind="ring", cx=300, cy=350, r=280,
                            inner_cx=300, inner_cy=350, inner_r=90),
        singles=SinglesParams(peak_thresh=12, box=7, box_thresh=50,
                              min_dist=9, local=7, ties="numpy1"),
        methods=(PileupMethod(
            name="baseline", kind="baseline_sum", baseline="percentile",
            baseline_percentile=30.0, rounding="nearest",
            calibration=CalibrationParams(
                measure="box", box=11, select="above_median",
                statistic="median", scope="frame", fallback="fixed",
                fixed_value=550.0)),)),
}


def preset(name):
    """The settings called name ("default" or one of LEGACY)."""
    if name == "default":
        return IonParams(name="default")
    return LEGACY[name]


def names():
    return ["default"] + list(LEGACY)
