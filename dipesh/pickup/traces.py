"""PicoScope files: finding the channels of each scope in a run folder and
reading one trace."""

import glob
import json
import os
from dataclasses import dataclass

import numpy as np

from .config import FILE_RE, ScopeConfig


@dataclass
class Trace:
    scope: str
    channel: str
    path: str
    t: np.ndarray                # µs, on the common experiment clock
    v_raw: np.ndarray
    v: np.ndarray                # after the RF notch, if applied
    delay_us: float
    pulse: dict
    rf: dict

    @property
    def key(self):
        return f"{self.scope}{self.channel}"


def channel_files(folder):
    """{tag_remainder: {channel: path}} for every Picoscope file in a folder."""
    groups = {}
    for p in glob.glob(os.path.join(folder, "Picoscope_ch*_*.json")):
        m = FILE_RE.search(os.path.basename(p))
        if m:
            groups.setdefault(m.group(2), {})[m.group(1).upper()] = p
    return groups


def discover_scopes(folder):
    """Guess scopes from filenames when no tags are configured: each distinct
    filename remainder is one acquisition, labelled A, B, ... in name order."""
    groups = channel_files(folder)
    return [ScopeConfig(chr(ord("A") + i), tag, None)
            for i, tag in enumerate(sorted(groups))]


def load_trace(path):
    """One PicoScope channel JSON -> (t_us, v, meta)."""
    with open(path) as f:
        data = json.load(f)
    rec = data[0] if isinstance(data, list) else data
    d = rec[next(iter(rec))]

    def scalar(node):
        return float(node["__value"]) if isinstance(node, dict) else float(node)

    v = np.asarray(d["Y_[V]"]["V"], dtype=float)
    t0, dt = scalar(d["t0"]), scalar(d["dt"])
    meta = {"t0": t0, "dt": dt, "n": len(v),
            "timestamp": d.get("Timestamp", {}).get("str", "")}
    return t0 + np.arange(len(v)) * dt, v, meta
