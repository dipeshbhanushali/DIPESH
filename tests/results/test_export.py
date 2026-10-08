"""counts.csv, spots.csv, params.json, marked images, the master archive."""
import csv
import json
import os

from dipesh import (DetectionParams, analyse, append_master, scan,
                                 write_outputs)
from dipesh.results import SPOT_COLUMNS


def results(tmp_path, run_folder):
    runs = tmp_path / "runs"
    runs.mkdir()
    run_folder(runs, 1, n=3, batman={"A": 1})
    run_folder(runs, 2, n=5, batman={"A": 2, "B": 7}, seed=3)
    return {"pbar": [analyse(i, DetectionParams()) for i in scan(str(runs))]}


def test_export_and_master_archive(tmp_path, run_folder):
    res = results(tmp_path, run_folder)

    out = tmp_path / "out"
    write_outputs(res, str(out), DetectionParams(), marked=True)
    rows = list(csv.DictReader(open(out / "counts.csv")))
    assert [int(r["pbar_count"]) for r in rows] == [3, 5]
    assert rows[0]["B"] == "" and rows[1]["B"] == "7.0"   # header grows
    assert len(list(csv.DictReader(open(out / "spots.csv")))) == 8
    assert len(os.listdir(out / "marked")) == 2
    assert json.load(open(out / "params.json"))["params"]["abs_thresh"] == 140.0

    m = tmp_path / "master"
    assert append_master(res, str(m)) == (2, 0)
    assert append_master(res, str(m)) == (0, 2)            # no duplicates
    assert append_master(res, str(m), replace_existing=True) == (2, 0)
    assert len(list(csv.DictReader(open(m / "master_runs.csv")))) == 2
    assert len(list(csv.DictReader(open(m / "master_spots.csv")))) == 8


def test_spots_csv_has_one_row_per_spot_with_the_measured_values(tmp_path,
                                                                 run_folder):
    res = results(tmp_path, run_folder)
    out = tmp_path / "out"
    write_outputs(res, str(out), DetectionParams(), marked=False)
    assert not (out / "marked").exists()
    rows = list(csv.DictReader(open(out / "spots.csv")))
    assert list(rows[0]) == ["dataset"] + SPOT_COLUMNS
    first = res["pbar"][0].spots[0]
    assert rows[0]["dataset"] == "pbar" and rows[0]["run_number"] == "1"
    assert (int(rows[0]["x"]), int(rows[0]["y"])) == (first.x, first.y)
    assert rows[0]["luminosity"] == f"{first.luminosity:.1f}"
    assert rows[0]["radial_sigma"] == f"{first.radial_sigma:.3f}"
    assert rows[0]["is_isolated"] == str(int(first.is_isolated))


def test_failed_runs_are_left_out_and_progress_is_reported(tmp_path,
                                                           run_folder):
    from dipesh import Item
    res = results(tmp_path, run_folder)
    res["pbar"].append(analyse(Item(str(tmp_path / "nope.tiff"), 9,
                                    str(tmp_path)), DetectionParams()))
    seen = []
    write_outputs(res, str(tmp_path / "out"), DetectionParams(), marked=True,
                  progress=lambda i, n: seen.append((i, n)))
    assert seen == [(1, 2), (2, 2)]
    assert len(list(csv.DictReader(open(tmp_path / "out" / "counts.csv")))) == 2
    params = json.load(open(tmp_path / "out" / "params.json"))
    assert params["datasets"] == {"pbar": 3}


def test_pickup_columns_are_written_next_to_the_counts(tmp_path, run_folder):
    res = results(tmp_path, run_folder)
    res["pbar"][0].pickup = {"pickup_A_chD_area": 0.25}
    write_outputs(res, str(tmp_path / "out"), DetectionParams(), marked=False)
    rows = list(csv.DictReader(open(tmp_path / "out" / "counts.csv")))
    assert rows[0]["pickup_A_chD_area"] == "0.25"
    assert rows[1]["pickup_A_chD_area"] == ""


def test_the_master_header_grows_and_old_rows_keep_their_values(tmp_path,
                                                                run_folder):
    res = results(tmp_path, run_folder)
    m = tmp_path / "master"
    append_master({"pbar": res["pbar"][:1]}, str(m))       # only parameter A
    append_master({"pbar": res["pbar"][1:]}, str(m))       # brings B
    rows = list(csv.DictReader(open(m / "master_runs.csv")))
    assert [r["run_number"] for r in rows] == ["1", "2"]
    assert rows[0]["A"] == "1.0" and rows[0]["B"] == "" and rows[1]["B"] == "7.0"
