"""
Ion analysis: counting ions in MCP release videos, including a pile-up disc
where they overlap, and the decay of the count with storage time.

    params       IonParams: every setting, JSON
    datasets     IonDataset, find_datasets, storage times, frames left out
    background   the per-pixel median background
    geometry     the region of single ions and the optional pile-up disc
    singles      single ions (find_spots)
    calibration  the single-ion signal (SIS)
    pileup       the ions in the pile-up disc from its light
    aggregate    the per-frame table and the totals
    run          analyse(dataset, params) -> IonResult
    errors       the error table of a dataset
    decay        N0 exp(-t / tau): weighted fit and two-point tau
    report       CSV and JSON of everything
    presets      named settings (and the legacy ones the tests use)

No Qt here: the GUI ("Ions" page) calls these.
"""

from .params import (AggregateParams, BackgroundParams, CalibrationParams,
                     IonParams, PileupMethod, RegionParams, SinglesParams)
from .datasets import (IonDataset, find_datasets, format_frames, load,
                       parse_frames, parse_storage_time, read_frame, save)
from .run import Cancelled, IonResult, analyse, frame_view, recount
from .presets import LEGACY, preset
from .errors import ErrorComponent, ErrorTable, ErrorValues, evaluate
from .decay import DecayFit, fit_decay, two_point_tau
from . import report
