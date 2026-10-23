"""Session: everything the pages share - the datasets, the current image,
the settings and the results."""

from PySide6 import QtCore

from ..pickup import PickupConfig
from ..single_image_analysis import DetectionParams
from .theme import SERIES, SYMBOLS


class Dataset:
    def __init__(self, name, items, index):
        self.name = name
        self.items = items
        self.colour = SERIES[index % len(SERIES)]
        self.symbol = SYMBOLS[index % len(SYMBOLS)]
        self.results = {}                     # item.key -> RunResult

    def result(self, item):
        return self.results.get(item.key)

    def done(self):
        return [self.results[i.key] for i in self.items
                if i.key in self.results and self.results[i.key].ok]


class Session(QtCore.QObject):
    datasetsChanged = QtCore.Signal()
    currentChanged = QtCore.Signal()
    paramsChanged = QtCore.Signal()
    resultsChanged = QtCore.Signal()
    liveChanged = QtCore.Signal()
    logged = QtCore.Signal(str, str)          # level, message

    def __init__(self):
        super().__init__()
        self.datasets = []
        self.params = DetectionParams()
        self.pickup = PickupConfig()
        self.results_params = None            # params the stored results used
        self.current = None                   # (Dataset, Item)
        self.live = None                      # RunResult for the current item
        self.n_skipped = 0                    # files looked at and not read
        self._added = 0

    # datasets
    def add(self, name, items):
        names = {d.name for d in self.datasets}
        base, k = name, 2
        while name in names:
            name, k = f"{base}-{k}", k + 1
        ds = Dataset(name, items, self._added)
        self._added += 1
        self.datasets.append(ds)
        self.datasetsChanged.emit()
        return ds

    def remove(self, ds, item=None):
        if item is None:
            self.datasets.remove(ds)
        else:
            ds.items.remove(item)
            ds.results.pop(item.key, None)
        if self.current and (self.current[0] is ds and
                             (item is None or self.current[1] is item)):
            self.current = None
            self.live = None
            self.currentChanged.emit()
        self.datasetsChanged.emit()
        self.resultsChanged.emit()

    def replace_items(self, ds, items):
        """Give a dataset a new list of items; results of items it keeps
        are kept."""
        keep = {i.key for i in items}
        ds.items = items
        ds.results = {k: r for k, r in ds.results.items() if k in keep}
        if (self.current and self.current[0] is ds
                and self.current[1].key not in keep):
            self.current = None
            self.live = None
            self.currentChanged.emit()
        self.datasetsChanged.emit()
        self.resultsChanged.emit()

    def set_current(self, ds, item):
        if self.current and self.current[1] is item:
            return
        self.current = (ds, item) if item else None
        self.currentChanged.emit()

    def set_params(self, params):
        if params != self.params:
            self.params = params
            self.paramsChanged.emit()

    @property
    def stale(self):
        has = any(d.results for d in self.datasets)
        return has and self.results_params != self.params

    def results(self):
        """{dataset name: [RunResult]} — only successful ones."""
        return {d.name: d.done() for d in self.datasets}

    def all_items(self):
        return [(d, i) for d in self.datasets for i in d.items]

    def log(self, msg, level="info"):
        self.logged.emit(level, msg)
