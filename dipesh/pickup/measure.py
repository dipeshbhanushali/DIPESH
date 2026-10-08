"""One run: every channel of every configured scope, on one experiment
clock."""

from .config import CHANNELS, PickupConfig
from .pulse import analyse_pulse
from .rf_filter import rf_notch
from .traces import Trace, channel_files, discover_scopes, load_trace


def measure(folder, batman, cfg: PickupConfig):
    """Every channel of every configured scope in one run folder.

    -> (traces: list[Trace], columns: dict)  columns are flat, ready to
       join onto the run's row: pickup_A_chD_peak_time_us, ...
    """
    groups = channel_files(folder)
    if not groups:
        return [], {}

    scopes = cfg.scopes
    # configured tags that match nothing -> fall back to what is on disk
    if not any(any(s.file_tag in tag for tag in groups) for s in scopes):
        scopes = discover_scopes(folder)

    traces, cols = [], {}
    for sc in scopes:
        files = {}
        for tag, chans in groups.items():
            if sc.file_tag and sc.file_tag in tag:
                files.update(chans)
        if not files:
            continue

        delay = 0.0
        if sc.delay_key and sc.delay_key in batman:
            try:
                delay = float(batman[sc.delay_key])
            except (TypeError, ValueError):
                delay = 0.0

        for ch in CHANNELS:
            if ch not in files:
                continue
            t, v_raw, meta = load_trace(files[ch])
            v, rf = v_raw, {"applied": False}
            if cfg.rf_enabled and ch in cfg.rf_channels:
                v, rf = rf_notch(v_raw, meta["dt"], cfg.rf_freq_mhz,
                                 cfg.rf_harmonics, cfg.rf_q)
                if not rf["applied"]:
                    v = v_raw
            ts = t + delay
            res = analyse_pulse(ts, v, cfg.pulse_nsigma, cfg.baseline_frac)
            traces.append(Trace(sc.label, ch, files[ch], ts, v_raw, v,
                                delay, res, rf))

            pre = f"pickup_{sc.label}_ch{ch}_"
            cols[pre + "peak_time_us"] = (res["peak_time_us"]
                                          if res["found"] else "")
            cols[pre + "amplitude_V"] = res["amplitude_V"]
            cols[pre + "area"] = res["area"]
            cols[pre + "width_us"] = res["width_us"]
        cols[f"pickup_{sc.label}_delay_us"] = delay
    return traces, cols
