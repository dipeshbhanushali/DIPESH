"""Settings of the pickup analysis: which scopes, the RF notch, the pulse
threshold."""

import re
from dataclasses import dataclass, field

CHANNELS = ("A", "B", "C", "D")
FILE_RE = re.compile(r"Picoscope_ch([A-D])_(.+)\.json$", re.IGNORECASE)


@dataclass
class ScopeConfig:
    label: str                   # "A", "B", ...
    file_tag: str                # text in the filename that identifies it
    delay_key: str | None = None # Batman key (µs) to shift this scope by


@dataclass
class PickupConfig:
    scopes: list = field(default_factory=lambda: [
        ScopeConfig("A", "PbarExtractionRange10", None),
        ScopeConfig("B", "PbarExtraction_2_Range10", "PT_TrapTime"),
    ])
    rf_enabled: bool = True
    rf_channels: tuple = ("D",)
    rf_freq_mhz: float = 26.92
    rf_harmonics: int = 3
    rf_q: float = 30.0
    pulse_nsigma: float = 5.0
    baseline_frac: float = 0.10
