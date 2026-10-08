"""
PicoScope pickup analysis — two scopes on one experiment clock.

Each run folder may hold up to two
PicoScope acquisitions, told apart by a tag in the filename:

    Picoscope_ch{A-D}_{tag}_....json

Scope A is the time reference. Scope B triggers later (after the trapping
wait), so its time axis is shifted by a Batman parameter in microseconds, and
both scopes then share one experiment clock.

The trap RF (26.92 MHz) swamps the pickup channel; a zero-phase IIR notch at
that frequency and its harmonics removes it without shifting the pulse.
"""

from .config import CHANNELS, FILE_RE, ScopeConfig, PickupConfig
from .traces import Trace, channel_files, discover_scopes, load_trace
from .rf_filter import rf_notch
from .pulse import analyse_pulse
# the function, not the module: `pickup.measure(folder, batman, cfg)` as before
from .measure import measure
