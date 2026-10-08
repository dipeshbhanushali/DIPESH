"""
Output files: counts.csv, spots.csv, params.json, marked images and the
growing master archive.
"""

import csv
import json
import os
from datetime import datetime

import numpy as np

from ..single_image_analysis import load_image, prepare


SPOT_COLUMNS = ["run_number", "spot_id", "x", "y", "luminosity", "radius_used",
                "area", "peak", "sum5x5", "radial_sigma", "concentration",
                "eccentricity", "profile_slope", "nn_dist", "is_isolated"]


def _spot_row(r, sid, s):
    return [r.item.run_number, sid, s.x, s.y, f"{s.luminosity:.1f}",
            s.radius_used, s.area, f"{s.peak:.1f}", f"{s.sum5x5:.1f}",
            f"{s.radial_sigma:.3f}", f"{s.concentration:.4f}",
            f"{s.eccentricity:.4f}", f"{s.profile_slope:.4f}",
            f"{s.nn_dist:.1f}", int(s.is_isolated)]


def _run_row(r, dataset):
    i = r.info
    row = {"run_number": r.item.run_number, "dataset": dataset,
           "pbar_count": r.n,
           "pbar_count_lum": f"{i.pbar_count_lum:.2f}",
           "integrated_lum": f"{i.integrated_lum:.1f}",
           "aperture_lum": f"{i.aperture_lum:.1f}",
           "noise_sigma": f"{i.sigma:.3f}",
           "threshold_used": f"{i.thresh:.1f}",
           "hot_pixels": i.hot_pixels,
           "image": r.item.path}
    row.update(r.pickup)
    row.update({k: r.batman[k] for k in sorted(r.batman)})
    return row


def write_outputs(results_by_dataset, out_dir, params, marked=True,
                  progress=None):
    """Write counts.csv, spots.csv, params.json and (optionally) marked
    images. results_by_dataset: {dataset_name: [RunResult, ...]}."""
    os.makedirs(out_dir, exist_ok=True)
    ok = [(d, r) for d, rs in results_by_dataset.items() for r in rs if r.ok]

    rows = [_run_row(r, d) for d, r in ok]
    fields = []
    for row in rows:
        fields += [k for k in row if k not in fields]
    with open(os.path.join(out_dir, "counts.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval="")
        w.writeheader()
        w.writerows(rows)

    with open(os.path.join(out_dir, "spots.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dataset"] + SPOT_COLUMNS)
        for d, r in ok:
            for sid, s in enumerate(r.spots):
                w.writerow([d] + _spot_row(r, sid, s))

    with open(os.path.join(out_dir, "params.json"), "w") as f:
        json.dump({"written": datetime.now().astimezone().isoformat(
                       timespec="seconds"),
                   "datasets": {d: len(rs) for d, rs in
                                results_by_dataset.items()},
                   "params": params.to_dict()}, f, indent=2)

    if marked:
        mdir = os.path.join(out_dir, "marked")
        os.makedirs(mdir, exist_ok=True)
        for k, (d, r) in enumerate(ok, 1):
            save_marked(r, os.path.join(mdir, f"{d}_{r.item.name}.png"), params)
            if progress:
                progress(k, len(ok))
    return out_dir


def save_marked(r, path, params):
    """A jet image with every counted spot circled — for checking by eye."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    img = load_image(r.item.path)
    if img is None:
        return
    diff, _, _ = prepare(img, params)
    h, w = diff.shape
    fig, ax = plt.subplots(figsize=(w / 120, h / 120))
    hi = float(np.percentile(diff, 99.95)) or 1.0
    ax.imshow(diff, cmap="jet", vmin=0, vmax=hi)
    for s in r.spots:
        ax.add_patch(plt.Circle((s.x, s.y), 12, edgecolor="lime",
                                facecolor="none", lw=1.0))
    if params.mcp_region:
        mx, my, mr = params.mcp_region
        ax.add_patch(plt.Circle((mx, my), mr, edgecolor="white",
                                facecolor="none", lw=1.2, ls=":"))
    ax.set_title(f"Run {r.item.name}  |  antiprotons: {r.n}",
                 loc="left", fontsize=11, fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def append_master(results_by_dataset, master_dir, replace_existing=False):
    """Append to master_runs.csv / master_spots.csv (the growing archive).

    The runs table's header grows as new Batman parameters appear; older rows
    get blanks in the new columns, nothing is ever dropped. A run already in
    the archive is skipped, or replaced when replace_existing is True.
    -> (n_runs_written, n_runs_skipped)
    """
    os.makedirs(master_dir, exist_ok=True)
    runs_path = os.path.join(master_dir, "master_runs.csv")
    spots_path = os.path.join(master_dir, "master_spots.csv")

    def _read(path):
        if not os.path.exists(path):
            return [], []
        with open(path, newline="") as f:
            rd = csv.DictReader(f)
            return list(rd.fieldnames or []), list(rd)

    rfields, rrows = _read(runs_path)
    sfields, srows = _read(spots_path)
    sfields = sfields or (["dataset"] + SPOT_COLUMNS)
    have = {str(r.get("run_number")) for r in rrows}

    written = skipped = 0
    for d, rs in results_by_dataset.items():
        for r in rs:
            if not r.ok:
                continue
            key = str(r.item.run_number)
            if key in have:
                if not replace_existing:
                    skipped += 1
                    continue
                rrows = [x for x in rrows if str(x.get("run_number")) != key]
                srows = [x for x in srows if str(x.get("run_number")) != key]
            row = _run_row(r, d)
            row["written"] = datetime.now().isoformat(timespec="seconds")
            rfields += [k for k in row if k not in rfields]
            rrows.append(row)
            for sid, s in enumerate(r.spots):
                srows.append(dict(zip(["dataset"] + SPOT_COLUMNS,
                                      [d] + _spot_row(r, sid, s))))
            have.add(key)
            written += 1

    for path, fields, rows in ((runs_path, rfields, rrows),
                               (spots_path, sfields, srows)):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, restval="",
                               extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    return written, skipped
