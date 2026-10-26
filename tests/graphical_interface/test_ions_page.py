"""The Ions page: datasets, the analysis in a worker, the release viewer,
calibration, pile-up, the error table, the decay fit and the export, in both
themes. What it shows is what ion_analysis computes."""
import dataclasses
import math
import os

import pytest
from PySide6 import QtCore, QtWidgets

from dipesh.ion_analysis import IonDataset, IonParams, analyse
from dipesh.ion_analysis.errors import ErrorComponent, ErrorTable
from dipesh.ion_analysis.params import (BackgroundParams, CalibrationParams,
                                        PileupMethod, RegionParams)
from gui import show

import ion_frames as F

RING = RegionParams("ring", cx=100, cy=100, r=90, inner_cx=100, inner_cy=100,
                    inner_r=10)
PARAMS = IonParams(background=BackgroundParams(mode="all"), region=RING,
                   methods=(PileupMethod(name="intensity"),
                            PileupMethod(name="exact", rounding="none")))


@pytest.fixture(scope="module")
def videos(tmp_path_factory):
    """Three storage times: fewer single ions the longer they were stored."""
    root = tmp_path_factory.mktemp("ion_videos")
    out = {}
    for t, scale in ((60, 1.0), (600, 0.6), (1800, 0.3)):
        plan = [(round(n * scale), round(d * scale)) for n, d in F.PLAN]
        out[t] = F.write(str(root / f"storage_{t}s"), plan)
    return out


def wait(page, qtbot):
    qtbot.waitUntil(lambda: page._thread is None, timeout=60000)
    QtWidgets.QApplication.processEvents()


@pytest.fixture
def ions(window, qtbot, videos):
    page = show(window, "ions")
    page.settings.set_params(PARAMS)
    page.add_datasets([IonDataset(f"{t} s", p, storage_time=t, series="scan")
                       for t, p in videos.items()])
    page.analyse(page.datasets)
    wait(page, qtbot)
    return page


def test_the_page_analyses_as_ion_analysis_does(ions, videos):
    assert [d.name for d in ions.datasets] == ["60 s", "600 s", "1800 s"]
    assert set(ions.results) == {"60 s", "600 s", "1800 s"}
    direct = analyse(IonDataset("x", videos[60]), PARAMS)
    assert ions.results["60 s"].totals == direct.totals
    assert ions.table.rowCount() == 3


def test_the_release_viewer_steps_through_frames_and_shows_the_ions(ions):
    ions.table.selectRow(0)
    ions.tabs.setCurrentIndex(0)
    view = ions.views[0]
    view.refresh()
    r = ions.results["60 s"]
    view.frame.setValue(3)
    QtWidgets.QApplication.processEvents()
    assert view.current_frame() == 3
    assert len(view.ions.data) == len(r.ions[3]) == r.rows[3].singles
    assert "single ions" in view.info.text()
    assert view.outer is not None and view.inner is not None   # ring + disc


def test_leaving_a_frame_out_counts_again_at_once(ions):
    ions.table.selectRow(0)
    view = ions.views[0]
    view.refresh()
    before = ions.results["60 s"].totals["intensity"].count
    view.frame.setValue(3)
    singles3 = ions.results["60 s"].rows[3].methods["intensity"].total
    view.left_out.setChecked(True)
    ds = ions.datasets[0]
    assert ds.exclude == (3,)
    assert ions.results["60 s"].totals["intensity"].count == before - singles3
    assert ions.table.item(0, 4).text() == "3"
    view.left_out.setChecked(False)
    assert ions.results["60 s"].totals["intensity"].count == before
    ions.table.item(0, 4).setText("0-1, 3")              # typed in the table
    assert ds.exclude == (0, 1, 3)


def test_dragging_the_disc_changes_the_settings(ions):
    ions.table.selectRow(0)
    view = ions.views[0]
    view.refresh()
    view.inner.setPos((80, 85))
    view.inner.sigRegionChangeFinished.emit(view.inner)
    reg = ions.settings.params().region
    assert (reg.inner_cx, reg.inner_cy, reg.inner_r) == (90, 95, 10)
    assert "•" in ions.table.item(0, 0).text()           # analysed before


def test_calibration_and_pileup_views(ions):
    ions.table.selectRow(0)
    show_tab(ions, "calibration")
    cal = ions.views[1]
    assert cal.method.currentText() == "intensity"
    assert "SIS" in cal.summary.text()
    assert cal.table.rowCount() == len(F.PLAN)
    assert cal.table.item(1, 2).text() == f"{F.ION_LIGHT:.4g}"
    assert cal.plot.getPlotItem().listDataItems()
    show_tab(ions, "pile-up")
    pile = ions.views[2]
    assert pile.table.rowCount() == len(F.PLAN)
    assert "intensity" in pile.summary.text()
    assert len(pile.plot.getPlotItem().listDataItems()) == 2


def show_tab(page, title):
    k = [v.title for v in page.views].index(title)
    page.tabs.setCurrentIndex(k)
    QtWidgets.QApplication.processEvents()
    page.views[k].refresh()
    return page.views[k]


def test_the_error_table_editor_sets_the_datasets_table(ions):
    ions.table.selectRow(0)
    view = show_tab(ions, "errors")
    view.add.click()
    view.add.click()
    view.table.cellWidget(1, 1).setCurrentText("fraction")
    view.table.cellWidget(1, 2).setCurrentText("systematic")
    view.table.item(1, 3).setText("0.1")
    t = ions.datasets[0].errors
    assert [c.kind for c in t.components] == ["poisson", "fraction"]
    n = ions.results["60 s"].totals["intensity"].count
    assert f"total {math.hypot(math.sqrt(n), 0.1 * n):.4g}" in view.result.text()
    assert view.table.item(0, 8).text() == f"{math.sqrt(n):.4g}"


def test_the_decay_fit_and_two_point_tau(ions):
    for ds in ions.datasets:
        ds.errors = ErrorTable((ErrorComponent("ten percent", "fraction",
                                               "systematic", fraction=0.1),))
    view = show_tab(ions, "decay")
    assert view.points.count() == 3
    view.do_fit()
    assert "tau =" in view.result.text()
    label, fit = ions.fits[0]
    from dipesh.ion_analysis import fit_decay
    pts = [(ds.storage_time, ions.results[ds.name].totals["intensity"].count,
            0.1 * ions.results[ds.name].totals["intensity"].count)
           for ds in ions.datasets]
    assert fit.tau == pytest.approx(fit_decay(*zip(*pts)).tau)
    view.first.setCurrentText("60 s")
    view.second.setCurrentText("1800 s")
    view.do_two()
    assert view.two_result.text().startswith("tau =")


def test_export(ions, tmp_path):
    view = show_tab(ions, "export")
    view.folder.setText(str(tmp_path / "report"))
    view.export()
    names = sorted(os.listdir(tmp_path / "report"))
    assert "totals.csv" in names and "report.json" in names
    assert sum(n.startswith("frames_") for n in names) == 3


def test_settings_save_load_and_presets(ions, tmp_path):
    p = str(tmp_path / "s.json")
    ions.settings.save(p)
    ions.settings.preset.setCurrentText("legacy storage")
    assert ions.settings.params().name == "legacy storage"
    ions.settings.load(p)
    assert ions.settings.params() == PARAMS
    ions.save_dataset(str(tmp_path / "d.json"), ions.datasets[0])
    ions.load_dataset(str(tmp_path / "d.json"))
    assert ions.datasets[-1].name == "60 s-2"


def test_an_analysis_can_be_cancelled(window, qtbot, videos):
    page = show(window, "ions")
    page.settings.set_params(PARAMS)
    page.add_datasets([IonDataset(f"v{k}", videos[60]) for k in range(4)])
    page.analyse(page.datasets)
    page.cancel()
    wait(page, qtbot)
    assert len(page.results) < 4
    assert page.analyse_btn.isEnabled()


@pytest.mark.parametrize("level", ["Strong", "Subtle"])
def test_every_view_in_glass(ions, level):
    win = ions.window()
    win.set_animation(False, save=False)
    win.set_glass_intensity(level, save=False)
    win.set_theme("Glass", save=False)
    ions.table.selectRow(0)
    for k in range(ions.tabs.count()):
        ions.tabs.setCurrentIndex(k)
        QtWidgets.QApplication.processEvents()
        ions.views[k].refresh()
        assert not win.grab().isNull()
