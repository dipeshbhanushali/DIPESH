"""
The settings of the ion analysis, as forms: one row per setting of
ion_analysis.IonParams, made from the dataclasses themselves, so every
setting there can be changed here. The words come from LABELS; the choices
from ion_analysis.params.
"""

import dataclasses
import json
import typing

from PySide6 import QtCore, QtWidgets

from ...ion_analysis import params as P
from ...ion_analysis.presets import names as preset_names, preset
from .base import combo, labelled

CHOICES = {
    "grey": P.GREY_RULES, "mode": P.BACKGROUND_MODES, "kind": None,
    "measure": P.MEASURES, "select": P.SELECTIONS, "statistic": P.STATISTICS,
    "frames_statistic": P.STATISTICS, "scope": P.SCOPES,
    "fallback": P.FALLBACKS, "background": P.SIGNAL_BACKGROUNDS,
    "baseline": P.BASELINES, "rounding": P.ROUNDINGS,
    "rule": P.AGGREGATE_RULES, "ties": P.TIES,
}
KIND_CHOICES = {P.RegionParams: P.REGIONS, P.PileupMethod: P.PILEUP_KINDS}

LABELS = {
    "mode": "made from", "n": "frames", "seed": "random seed",
    "kind": "kind", "x0": "left", "y0": "top", "x1": "right", "y1": "bottom",
    "cx": "centre x", "cy": "centre y", "r": "radius",
    "inner_cx": "disc centre x", "inner_cy": "disc centre y",
    "inner_r": "disc radius",
    "peak_thresh": "peak above", "box": "box (px)", "box_thresh": "box sum above",
    "min_dist": "min separation", "local": "local max (px)",
    "spread_min": "spread above", "ties": "equal peaks",
    "name": "name", "pixel_thresh": "pixels above", "baseline": "baseline",
    "baseline_percentile": "baseline percentile",
    "baseline_value": "baseline value", "min_sum": "blob above",
    "rounding": "rounding", "signal_decimals": "S decimals",
    "measure": "measure", "radius": "aperture radius",
    "background": "background per px", "background_value": "background value",
    "sparsest_frames": "sparsest frames", "margin": "keep-out margin",
    "positive": "only positive", "select": "ions used",
    "isolation_px": "isolated by (px)", "statistic": "statistic",
    "scope": "one SIS per", "frames_statistic": "over frames",
    "min_ions": "frames with ions >=", "fallback": "no SIS: use",
    "fixed_value": "fixed SIS", "use_excluded": "left-out frames count",
    "decimals": "SIS decimals", "rule": "add up", "active_threshold":
    "frames above", "grey": "colour to grey",
}


def _optional(tp):
    """(name of the base type, None allowed) of a dataclass field's type."""
    args = typing.get_args(tp)
    if args:                                       # float | None
        base = [a for a in args if a is not type(None)][0]
        return base.__name__, type(None) in args
    return getattr(tp, "__name__", str(tp)), False


class Form(QtWidgets.QWidget):
    """A form for one frozen dataclass. value() gives a new one."""
    changed = QtCore.Signal()

    def __init__(self, value, skip=()):
        super().__init__()
        self._value = value
        self.widgets = {}
        lay = QtWidgets.QFormLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setVerticalSpacing(4)
        for f in dataclasses.fields(value):
            if f.name in skip or f.name == "calibration":
                continue
            choices = CHOICES.get(f.name)
            if f.name == "kind":
                choices = KIND_CHOICES.get(type(value))
            w = self._widget(f, choices)
            if w is None:
                continue
            self.widgets[f.name] = w
            text = LABELS.get(f.name, f.name.replace("_", " "))
            if isinstance(w, QtWidgets.QComboBox):
                lay.addRow(labelled(w, text))
            elif isinstance(w, QtWidgets.QCheckBox):
                w.setText(text)
                lay.addRow(w)
            else:
                lay.addRow(text, w)
        self.set_value(value)

    def _widget(self, f, choices):
        base, opt = _optional(f.type)
        if choices:
            w = combo(choices)
            w.currentIndexChanged.connect(self.changed)
            return w
        if base == "bool":
            w = QtWidgets.QCheckBox()
            w.toggled.connect(self.changed)
            return w
        if opt or base == "str":
            w = QtWidgets.QLineEdit()
            if opt:
                w.setPlaceholderText("none")
            w.editingFinished.connect(self.changed)
            return w
        if base == "int":
            w = QtWidgets.QSpinBox()
            w.setRange(0, 1_000_000)
        elif base == "float":
            w = QtWidgets.QDoubleSpinBox()
            w.setRange(-1e9, 1e9)
            w.setDecimals(3)
        else:
            return None                           # tuples: not edited here
        w.setKeyboardTracking(False)
        w.valueChanged.connect(self.changed)
        return w

    def set_value(self, value):
        self._value = value
        for name, w in self.widgets.items():
            v = getattr(value, name)
            w.blockSignals(True)
            if isinstance(w, QtWidgets.QComboBox):
                w.setCurrentText(str(v))
            elif isinstance(w, QtWidgets.QCheckBox):
                w.setChecked(bool(v))
            elif isinstance(w, QtWidgets.QLineEdit):
                w.setText("" if v is None else str(v))
            else:
                w.setValue(v)
            w.blockSignals(False)

    def value(self):
        kw = {}
        for f in dataclasses.fields(self._value):
            w = self.widgets.get(f.name)
            if w is None:
                continue
            base, opt = _optional(f.type)
            if isinstance(w, QtWidgets.QComboBox):
                kw[f.name] = w.currentText()
            elif isinstance(w, QtWidgets.QCheckBox):
                kw[f.name] = w.isChecked()
            elif isinstance(w, QtWidgets.QLineEdit):
                text = w.text().strip()
                if opt and not text:
                    kw[f.name] = None
                elif base == "int":
                    kw[f.name] = int(text)
                elif base == "float":
                    kw[f.name] = float(text)
                else:
                    kw[f.name] = text
            else:
                kw[f.name] = w.value()
        return dataclasses.replace(self._value, **kw)


class SettingsPanel(QtWidgets.QScrollArea):
    """Every setting of the analysis. paramsChanged when one changes."""
    paramsChanged = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        inner = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(inner)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(8)
        self.setWidget(inner)

        row = QtWidgets.QHBoxLayout()
        self.preset = combo(preset_names())
        self.preset.setToolTip("Start from these settings. The legacy ones "
                               "repeat earlier analyses value for value")
        row.addWidget(labelled(self.preset, "start from"), 1)
        lay.addLayout(row)
        row = QtWidgets.QHBoxLayout()
        self.load_btn = QtWidgets.QPushButton("Load…")
        self.save_btn = QtWidgets.QPushButton("Save…")
        row.addWidget(self.load_btn)
        row.addWidget(self.save_btn)
        lay.addLayout(row)

        self._params = preset("default")
        self.grey = combo(P.GREY_RULES)
        lay.addWidget(labelled(self.grey, "colour to grey"))
        self.forms = {}
        for key, title, value in (
                ("background", "background", self._params.background),
                ("region", "region and pile-up disc", self._params.region),
                ("singles", "single ions", self._params.singles),
                ("aggregate", "frames add up", self._params.aggregate)):
            box = QtWidgets.QGroupBox(title)
            bl = QtWidgets.QVBoxLayout(box)
            f = Form(value)
            f.changed.connect(self._changed)
            bl.addWidget(f)
            self.forms[key] = f
            lay.addWidget(box)

        box = QtWidgets.QGroupBox("pile-up methods")
        bl = QtWidgets.QVBoxLayout(box)
        self.method_list = QtWidgets.QListWidget()
        self.method_list.setMaximumHeight(80)
        bl.addWidget(self.method_list)
        row = QtWidgets.QHBoxLayout()
        self.add_method = QtWidgets.QPushButton("Add")
        self.remove_method = QtWidgets.QPushButton("Remove")
        row.addWidget(self.add_method)
        row.addWidget(self.remove_method)
        bl.addLayout(row)
        self.method_form = Form(P.PileupMethod())
        self.cal_form = Form(P.CalibrationParams())
        bl.addWidget(self.method_form)
        cal = QtWidgets.QLabel("single-ion signal")
        cal.setObjectName("heading")
        bl.addWidget(cal)
        bl.addWidget(self.cal_form)
        lay.addWidget(box)
        lay.addStretch(1)
        self.methods = []

        self.grey.currentIndexChanged.connect(self._changed)
        self.method_form.changed.connect(self._method_changed)
        self.cal_form.changed.connect(self._method_changed)
        self.method_list.currentRowChanged.connect(self._show_method)
        self.add_method.clicked.connect(self._add_method)
        self.remove_method.clicked.connect(self._remove_method)
        self.preset.currentTextChanged.connect(
            lambda name: self.set_params(preset(name)))
        self.load_btn.clicked.connect(self._load)
        self.save_btn.clicked.connect(self._save)
        self.set_params(self._params)

    # the settings
    def params(self):
        return self._params

    def set_params(self, params):
        params.check()
        self._params = params
        self.grey.blockSignals(True)
        self.grey.setCurrentText(params.grey)
        self.grey.blockSignals(False)
        for key, f in self.forms.items():
            f.set_value(getattr(params, key))
        self.methods = list(params.methods)
        self._fill_methods(0 if self.methods else -1)
        self.paramsChanged.emit()

    def _fill_methods(self, select):
        self.method_list.blockSignals(True)
        self.method_list.clear()
        self.method_list.addItems([m.name for m in self.methods])
        self.method_list.blockSignals(False)
        self.method_list.setCurrentRow(select)
        self._show_method(select)

    def _show_method(self, k):
        on = 0 <= k < len(self.methods)
        self.method_form.setEnabled(on)
        self.cal_form.setEnabled(on)
        if on:
            self.method_form.set_value(self.methods[k])
            self.cal_form.set_value(self.methods[k].calibration)

    def _rebuild(self):
        try:
            p = self._params.with_(
                grey=self.grey.currentText(),
                methods=tuple(self.methods),
                **{k: f.value() for k, f in self.forms.items()}).check()
        except (ValueError, TypeError):
            return False                          # not allowed: keep the last
        self._params = p
        self.paramsChanged.emit()
        return True

    def _changed(self):
        self._rebuild()

    def _method_changed(self):
        k = self.method_list.currentRow()
        if not 0 <= k < len(self.methods):
            return
        m = dataclasses.replace(self.method_form.value(),
                                calibration=self.cal_form.value())
        self.methods[k] = m
        self.method_list.item(k).setText(m.name)
        self._rebuild()

    def _add_method(self):
        names = {m.name for m in self.methods}
        k = 1
        while f"method {k}" in names:
            k += 1
        self.methods.append(P.PileupMethod(name=f"method {k}"))
        self._fill_methods(len(self.methods) - 1)
        self._rebuild()

    def _remove_method(self):
        k = self.method_list.currentRow()
        if 0 <= k < len(self.methods):
            del self.methods[k]
            self._fill_methods(min(k, len(self.methods) - 1))
            self._rebuild()

    def set_region(self, region):
        """From the viewer, when a circle is dragged."""
        self.forms["region"].set_value(region)
        self._rebuild()

    # files
    def _load(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load ion settings", "", "JSON (*.json)")
        if path:
            self.load(path)

    def load(self, path):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        self.set_params(P.IonParams.from_dict(d.get("params", d)))

    def _save(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save ion settings", "ion_settings.json", "JSON (*.json)")
        if path:
            self.save(path)

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._params.to_json())
