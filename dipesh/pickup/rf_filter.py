"""The trap RF (26.92 MHz) swamps the pickup channel; a zero-phase IIR notch
at that frequency and its harmonics removes it without shifting the pulse."""


def rf_notch(v, dt_us, freq_mhz=26.92, harmonics=3, q=30.0):
    """Notch out freq_mhz and its harmonics, zero-phase. -> (v, info).
    Frequencies at or above Nyquist are skipped (they would alias)."""
    from scipy import signal
    fs = 1.0 / dt_us
    nyq = fs / 2.0
    out = v.astype(float).copy()
    notched = []
    for k in range(1, int(harmonics) + 1):
        f = freq_mhz * k
        if f >= nyq:
            break
        b, a = signal.iirnotch(f / nyq, q)
        out = signal.filtfilt(b, a, out)
        notched.append(f)
    info = {"applied": bool(notched), "notched_MHz": notched,
            "fs_MHz": fs, "nyquist_MHz": nyq}
    if not notched:
        info["reason"] = (f"{freq_mhz} MHz is above Nyquist ({nyq:.1f} MHz) "
                          "at this sample rate")
    return out, info
