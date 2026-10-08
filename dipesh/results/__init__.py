"""
Results of whole runs.

    run      RunResult, RUN_METRICS, analyse
    export   write_outputs, save_marked, append_master
    trends   average_xy, fit_curve
"""

from .run import RunResult, RUN_METRICS, analyse
from .export import SPOT_COLUMNS, write_outputs, save_marked, append_master
from .trends import average_xy, fit_curve
