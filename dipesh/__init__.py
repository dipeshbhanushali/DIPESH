"""
DIPESH - Detection and Imaging of Pbar Events, Spots and Hits.

Antiproton counting and analysis for MCP / phosphor camera images.

Desktop app:   dipesh          (or: python -m dipesh)

Scripting:

    from dipesh import scan, analyse, DetectionParams
    items = scan(r"C:\\DATA\\my_runs")
    results = [analyse(it, DetectionParams()) for it in items]
    print(sum(r.n for r in results), "antiprotons")
"""

from .single_image_analysis import (DetectionParams, DEFAULT_PARAMS, Item,
                                    Spot, DetectionInfo, SPOT_FEATURES, scan,
                                    find_run_folders, find_tiff, load_image,
                                    parse_batman, detect, prepare, to_float)
from .results import (RunResult, analyse, write_outputs, append_master,
                      average_xy, fit_curve, RUN_METRICS)
from .clustering_recognition import separation_score, best_threshold, pca
from .pickup import PickupConfig, ScopeConfig, measure as measure_pickup

from ._about import VERSION as __version__
