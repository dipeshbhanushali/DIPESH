"""The RF notch: removes the trap RF and its harmonics, moves nothing."""
import numpy as np
import pytest

from dipesh.pickup import rf_notch

DT = 0.008                                   # µs -> 125 MS/s, Nyquist 62.5 MHz
T = np.arange(6000) * DT


def amplitude_at(v, f_mhz):
    """Amplitude of the f_mhz component, from the middle of the trace (the
    ends carry the filter's edge transient)."""
    t, v = T[1000:-1000], v[1000:-1000]
    return 2 * abs(np.mean(v * np.exp(-2j * np.pi * f_mhz * t)))


def test_notch_skips_frequencies_above_nyquist():
    v = np.zeros(1000)
    _, info = rf_notch(v, dt_us=0.1, freq_mhz=26.92)     # 10 MS/s
    assert not info["applied"] and "Nyquist" in info["reason"]


def test_the_fundamental_and_its_harmonic_are_notched():
    """4 mV at 26.92 MHz and 1.2 mV at 53.84 MHz: both below 1 % after the notch."""
    v = (0.004 * np.sin(2 * np.pi * 26.92 * T)
         + 0.0012 * np.sin(2 * np.pi * 53.84 * T))
    out, info = rf_notch(v, DT, 26.92, harmonics=3, q=30.0)
    assert amplitude_at(v, 26.92) == pytest.approx(0.004, rel=0.01)
    assert amplitude_at(out, 26.92) < 0.01 * 0.004
    assert amplitude_at(out, 53.84) < 0.01 * 0.0012


def test_harmonics_at_or_above_nyquist_are_left_out():
    """At 125 MS/s: 26.92 and 53.84 MHz are notched, 80.76 MHz would alias."""
    _, info = rf_notch(np.zeros(2000), DT, 26.92, harmonics=3)
    assert info["applied"] and info["notched_MHz"] == pytest.approx([26.92, 53.84])
    assert info["nyquist_MHz"] == pytest.approx(62.5)


def test_one_harmonic_leaves_the_second_alone():
    v = (0.004 * np.sin(2 * np.pi * 26.92 * T)
         + 0.0012 * np.sin(2 * np.pi * 53.84 * T))
    out, info = rf_notch(v, DT, 26.92, harmonics=1)
    assert info["notched_MHz"] == [26.92]
    assert amplitude_at(out, 26.92) < 0.01 * 0.004
    assert amplitude_at(out, 53.84) == pytest.approx(0.0012, rel=0.05)


def test_a_frequency_away_from_the_notch_passes():
    """A 5 MHz signal keeps its amplitude within 1 %."""
    v = 0.01 * np.sin(2 * np.pi * 5.0 * T)
    out, _ = rf_notch(v, DT, 26.92, harmonics=3)
    assert amplitude_at(out, 5.0) == pytest.approx(0.01, rel=0.01)


@pytest.mark.parametrize("t_pulse", [12.0, 20.004, 31.5])
def test_the_notch_is_zero_phase_the_pulse_does_not_move(t_pulse):
    """filtfilt runs the filter forwards and backwards: the peak of a 0.35 µs pulse stays within one sample (8 ns), with and without RF on top."""
    pulse = -0.006 * np.exp(-0.5 * ((T - t_pulse) / 0.35) ** 2)
    for v in (pulse, pulse + 0.004 * np.sin(2 * np.pi * 26.92 * T)):
        out, _ = rf_notch(v, DT, 26.92, harmonics=3)
        assert abs(T[np.argmin(out)] - T[np.argmin(pulse)]) <= DT


def test_the_notch_keeps_the_size_of_the_pulse():
    """A 0.35 µs pulse has almost nothing at 27 MHz: amplitude and area within 2 %."""
    pulse = 0.006 * np.exp(-0.5 * ((T - 20.0) / 0.35) ** 2)
    out, _ = rf_notch(pulse, DT, 26.92, harmonics=3)
    assert out.max() == pytest.approx(0.006, rel=0.02)
    assert out.sum() == pytest.approx(pulse.sum(), rel=0.02)


def test_the_input_trace_is_not_modified():
    v = 0.004 * np.sin(2 * np.pi * 26.92 * T)
    keep = v.copy()
    rf_notch(v, DT)
    assert np.array_equal(v, keep)
