"""One run folder: scopes, channels, delays, flat columns."""
from dipesh import PickupConfig, ScopeConfig, measure_pickup
from dipesh.pickup import (channel_files, discover_scopes,
                                        load_trace)


def test_rf_notch_recovers_a_pulse_buried_in_rf(tmp_path, picoscope):
    picoscope(tmp_path, "PbarExtractionRange10")
    with_rf, _ = measure_pickup(str(tmp_path), {}, PickupConfig(rf_enabled=False))
    clean, _ = measure_pickup(str(tmp_path), {}, PickupConfig())
    raw = next(t for t in with_rf if t.key == "AD").pulse
    got = next(t for t in clean if t.key == "AD").pulse
    assert not raw["found"]                         # RF swamps it
    assert got["found"]
    assert abs(got["peak_time_us"] - 12.0) < 0.05
    assert abs(got["amplitude_V"] - 0.006) < 0.001


def test_scope_b_is_shifted_by_its_batman_delay(tmp_path, picoscope):
    picoscope(tmp_path, "PbarExtractionRange10", t_pulse=12.0)
    picoscope(tmp_path, "PbarExtraction_2_Range10", t_pulse=18.0)
    traces, cols = measure_pickup(str(tmp_path), {"PT_TrapTime": 5000.0},
                                  PickupConfig())
    b = next(t for t in traces if t.key == "BD").pulse
    assert abs(b["peak_time_us"] - 5018.0) < 0.05
    assert cols["pickup_B_delay_us"] == 5000.0


def test_scopes_are_found_from_filenames_when_tags_do_not_match(tmp_path,
                                                                picoscope):
    picoscope(tmp_path, "SomeOtherTag")
    traces, _ = measure_pickup(str(tmp_path), {},
                               PickupConfig(scopes=[ScopeConfig("A", "nope")]))
    assert len(traces) == 4


def test_a_folder_without_picoscope_files_gives_nothing(tmp_path):
    assert measure_pickup(str(tmp_path), {}, PickupConfig()) == ([], {})


def test_the_notch_is_applied_only_to_the_chosen_channels(tmp_path, picoscope):
    picoscope(tmp_path, "PbarExtractionRange10")
    traces, _ = measure_pickup(str(tmp_path), {}, PickupConfig())
    assert {t.channel: t.rf["applied"] for t in traces} == {
        "A": False, "B": False, "C": False, "D": True}
    d = next(t for t in traces if t.channel == "D")
    assert d.v is not d.v_raw and len(d.v) == len(d.v_raw)


def test_the_columns_are_flat_and_named_by_scope_and_channel(tmp_path,
                                                             picoscope):
    picoscope(tmp_path, "PbarExtractionRange10")
    _, cols = measure_pickup(str(tmp_path), {}, PickupConfig())
    assert cols["pickup_A_delay_us"] == 0.0
    for ch in "ABCD":
        for what in ("peak_time_us", "amplitude_V", "area", "width_us"):
            assert f"pickup_A_ch{ch}_{what}" in cols
    assert cols["pickup_A_chB_peak_time_us"] == ""   # no pulse on B
    assert abs(cols["pickup_A_chD_peak_time_us"] - 12.0) < 0.05


def test_files_are_grouped_by_scope_tag_and_channel(tmp_path, picoscope):
    picoscope(tmp_path, "PbarExtractionRange10")
    picoscope(tmp_path, "PbarExtraction_2_Range10")
    groups = channel_files(str(tmp_path))
    assert sorted(groups) == ["PbarExtractionRange10_x",
                              "PbarExtraction_2_Range10_x"]
    assert all(sorted(g) == list("ABCD") for g in groups.values())
    assert [(s.label, s.file_tag) for s in discover_scopes(str(tmp_path))] == [
        ("A", "PbarExtractionRange10_x"), ("B", "PbarExtraction_2_Range10_x")]


def test_a_trace_file_gives_its_time_axis_in_microseconds(tmp_path, picoscope):
    """t = t0 + i dt with t0 = -10 µs, dt = 0.008 µs, 6000 samples."""
    picoscope(tmp_path, "PbarExtractionRange10")
    t, v, meta = load_trace(str(tmp_path / "Picoscope_chD_PbarExtractionRange10_x.json"))
    assert len(t) == len(v) == meta["n"] == 6000
    assert t[0] == -10.0 and abs(t[1] - t[0] - 0.008) < 1e-12
