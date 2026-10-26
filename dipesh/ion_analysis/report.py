"""
Everything as files: per dataset the per-frame table (frames_<name>.csv);
for all datasets the totals with their errors (totals.csv) and every error
component (errors.csv); and all of it, with the settings and the decay
fits, in report.json. Excluded frames are marked in every table.
"""

import csv
import json
import os
import re

from .datasets import format_frames
from .errors import evaluate


def _safe(name):
    return re.sub(r"[^\w.-]+", "_", name).strip("_") or "dataset"


def frames_rows(result):
    """The per-frame table as rows of dicts."""
    out = []
    for row in result.rows:
        d = {"frame": row.frame, "excluded": int(row.excluded),
             "single_ions": row.singles}
        if result.params.region.pileup:
            d["disc_light"] = round(row.disc_sum, 3)
        for name, m in row.methods.items():
            d[f"{name}: sis"] = "" if m.sis is None else round(m.sis, 3)
            d[f"{name}: sis_ions"] = m.sis_ions
            d[f"{name}: disc_signal"] = round(m.signal, 3)
            d[f"{name}: disc_ions"] = m.inner
            d[f"{name}: total"] = m.total
            d[f"{name}: skipped"] = int(m.skipped)
        out.append(d)
    return out


def totals_rows(results):
    """One row per dataset and method: count, its parts, the frames used and
    left out, and the error table's errors (for the table's method)."""
    out = []
    for r in results:
        ds = r.dataset
        errs = evaluate(ds.errors, r)
        for name, t in r.totals.items():
            mine = name == errs.method
            out.append({
                "dataset": ds.name, "series": ds.series,
                "storage_time_s": "" if ds.storage_time is None else ds.storage_time,
                "method": name, "count": t.count, "single_ions": t.singles,
                "disc_ions": t.inner, "frames_used": t.frames,
                "frames_excluded": format_frames(r.excluded),
                "error_statistical": errs.statistical if mine else "",
                "error_systematic": errs.systematic if mine else "",
                "error_total": errs.total if mine else "",
            })
    return out


def errors_rows(results):
    out = []
    for r in results:
        errs = evaluate(r.dataset.errors, r)
        for name, group, value in errs.components:
            out.append({"dataset": r.dataset.name, "method": errs.method,
                        "component": name, "group": group, "value": value})
    return out


def _write_csv(path, rows):
    fields = []
    for row in rows:
        fields += [k for k in row if k not in fields]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval="")
        w.writeheader()
        w.writerows(rows)


def fit_dict(fit, label=""):
    return {"label": label, "n0": fit.n0, "n0_err": fit.n0_err,
            "tau_s": fit.tau, "tau_err_s": fit.tau_err,
            "covariance": fit.covariance, "chi2": fit.chi2, "dof": fit.dof,
            "reduced_chi2": fit.reduced_chi2,
            "points": [{"t_s": t, "count": n, "error": e}
                       for t, n, e in fit.points]}


def write(folder, results, fits=()):
    """Write the report of results (run.IonResult) and decay fits
    ((label, decay.DecayFit) pairs) into folder. -> list of files written"""
    os.makedirs(folder, exist_ok=True)
    written = []
    for r in results:
        p = os.path.join(folder, f"frames_{_safe(r.dataset.name)}.csv")
        _write_csv(p, frames_rows(r))
        written.append(p)
    for name, rows in (("totals.csv", totals_rows(results)),
                       ("errors.csv", errors_rows(results))):
        p = os.path.join(folder, name)
        _write_csv(p, rows)
        written.append(p)
    doc = {"datasets": [], "fits": [fit_dict(f, label) for label, f in fits]}
    for r in results:
        doc["datasets"].append({
            "dataset": r.dataset.to_dict(),
            "settings": r.params.to_dict(),
            "excluded_frames": r.excluded,
            "totals": {n: vars(t) for n, t in r.totals.items()},
            "methods": {n: vars(m) for n, m in r.methods.items()},
            "errors": vars(evaluate(r.dataset.errors, r)),
            "frames": frames_rows(r),
        })
    p = os.path.join(folder, "report.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    written.append(p)
    return written
