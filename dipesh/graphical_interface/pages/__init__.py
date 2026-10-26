"""
The eight analyses on the top bar.

    image      the current frame, every counted spot drawn at its true
               aperture, settings live
    spots      every spot's measurements, as a table
    histogram  one feature across datasets; separation and best cut
    pca        all shape and brightness features at once
    plots      any run quantity against any Batman parameter, averaged, fitted
    pickup     PicoScope traces for the current run, RF notch, pulse timing
    ions       ion release videos: single ions, pile-up disc, calibration,
               errors, decay with storage time (ion_analysis)
    learn      (in graphical_interface/learn) under construction
"""

from .base import Page
from .image import ImagePage
from .spots import SpotsPage
from .histogram import HistogramPage
from .pca import PcaPage
from .plots import PlotsPage
from .pickup import PickupPage
from .ions import IonsPage
from ..learn import LearnPage


def make_pages(session):
    return [ImagePage(session), SpotsPage(session), HistogramPage(session),
            PcaPage(session), PlotsPage(session), PickupPage(session),
            IonsPage(session), LearnPage(session)]
