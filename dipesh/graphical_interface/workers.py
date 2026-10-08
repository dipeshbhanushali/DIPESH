"""
Background work: live detection of the current image, Run all, Export and
the pickup measurement of the current run.

Everything here emits signals from a thread that is not the GUI thread.
Connect them only to bound slots of an object living in the GUI thread.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6 import QtCore

from ..pickup import measure as measure_pickup
from ..results import RunResult, analyse, append_master, write_outputs


class _LiveSignals(QtCore.QObject):
    done = QtCore.Signal(int, object)


class _LiveJob(QtCore.QRunnable):
    def __init__(self, gen, item, params, sig):
        super().__init__()
        self.gen, self.item, self.params, self.sig = gen, item, params, sig

    def run(self):
        try:
            r = analyse(self.item, self.params)
        except Exception as e:                    # noqa: BLE001 — shown in UI
            r = RunResult(self.item, error=str(e))
        self.sig.done.emit(self.gen, r)


class LiveDetector(QtCore.QObject):
    """Re-detects the current image whenever it or the settings change.

    Detection takes ~85 ms on a 1280x1024 frame: fast enough to feel live,
    too slow for the UI thread. Jobs run in a pool; a generation number
    makes sure only the newest result is ever shown.
    """

    def __init__(self, session):
        super().__init__()
        self.s = session
        self.pool = QtCore.QThreadPool.globalInstance()
        # the signal object is made here, in the GUI thread, and kept for the
        # life of the detector; jobs emit on it from pool threads
        self.sig = _LiveSignals()
        self.sig.done.connect(self._done, QtCore.Qt.QueuedConnection)
        self.gen = 0
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._start)
        session.currentChanged.connect(self.timer.start)
        session.paramsChanged.connect(self.timer.start)

    def _start(self):
        if not self.s.current:
            self.s.live = None
            self.s.liveChanged.emit()
            return
        self.gen += 1
        self.pool.start(_LiveJob(self.gen, self.s.current[1], self.s.params,
                                 self.sig))

    @QtCore.Slot(int, object)
    def _done(self, gen, r):
        if gen != self.gen:
            return                                # superseded
        if self.s.current and self.s.current[1] is r.item:
            self.s.live = r
            self.s.liveChanged.emit()


class RunAllWorker(QtCore.QObject):
    progress = QtCore.Signal(int, int)
    one = QtCore.Signal(object, object)          # Dataset, RunResult
    finished = QtCore.Signal(float, int, int)    # seconds, n_ok, n_failed

    def __init__(self, jobs, params, pickup_cfg):
        super().__init__()
        self.jobs, self.params, self.pickup = jobs, params, pickup_cfg
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def _work(self, item):
        r = analyse(item, self.params)
        if r.ok:
            try:
                _, cols = measure_pickup(item.folder, r.batman, self.pickup)
                r.pickup = cols
            except Exception:                     # noqa: BLE001
                pass                              # no / unreadable pickup
        return r

    @QtCore.Slot()
    def run(self):
        t0 = time.perf_counter()
        n_ok = n_bad = 0
        workers = max(2, (os.cpu_count() or 4) - 1)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(self._work, it): ds for ds, it in self.jobs}
            for k, f in enumerate(as_completed(futs), 1):
                if self.cancelled:
                    for g in futs:
                        g.cancel()
                    break
                r = f.result()
                n_ok += r.ok
                n_bad += not r.ok
                self.one.emit(futs[f], r)
                self.progress.emit(k, len(futs))
        self.finished.emit(time.perf_counter() - t0, n_ok, n_bad)


class ExportWorker(QtCore.QObject):
    progress = QtCore.Signal(int, int)
    finished = QtCore.Signal(bool, str)

    def __init__(self, results, out_dir, params, marked, master_dir, replace):
        super().__init__()
        self.args = (results, out_dir, params, marked, master_dir, replace)

    @QtCore.Slot()
    def run(self):
        results, out_dir, params, marked, master_dir, replace = self.args
        try:
            write_outputs(results, out_dir, params, marked,
                          progress=lambda i, n: self.progress.emit(i, n))
            msg = f"wrote counts.csv, spots.csv, params.json to {out_dir}"
            if master_dir:
                w, s = append_master(results, master_dir, replace)
                msg += f"; master: {w} runs added, {s} already there"
            self.finished.emit(True, msg)
        except Exception as e:                    # noqa: BLE001
            self.finished.emit(False, f"export failed: {e}")


class _PickupSignals(QtCore.QObject):
    done = QtCore.Signal(int, object, object)


class _PickupJob(QtCore.QRunnable):
    def __init__(self, gen, folder, batman, cfg, sig):
        super().__init__()
        self.args = (gen, folder, batman, cfg, sig)

    def run(self):
        gen, folder, batman, cfg, sig = self.args
        try:
            traces, cols = measure_pickup(folder, batman, cfg)
            sig.done.emit(gen, traces, None)
        except Exception as e:                    # noqa: BLE001
            sig.done.emit(gen, [], str(e))
