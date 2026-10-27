"""
The main window.

Layout
    top     : analysis bar  (image, spots, histogram, pca, plots, pickup, learn)
              plus run all / export
    left    : datasets - every folder or batch of images you add, its runs
    centre  : the current analysis
    right   : detection settings (image and spots pages)
    bottom  : console

View switches between the Phosphor and Glass looks (theme.py, glass.py),
sets the Glass intensity (Subtle or Strong) and turns the drifting Strong
background on or off. The choices are kept in QSettings under "theme",
"glass_intensity" and "animate_background".
"""

from PySide6 import QtCore, QtGui, QtWidgets

from .. import __version__, _about
from .pages import make_pages
from .session import Session
from . import glass as glass_ui
from .glass import (Backdrop, Frost, PopupGlass, plot_frames, reduced_motion,
                    windows_frame)
from .theme import (APP_NAME, INTENSITIES, PHOSPHOR, THEMES, TUBE, current,
                    glow, intensity, muted, restyle_plots, set_intensity,
                    use_theme)
from .widgets import Console, DetectionPanel, ExportDialog, SidePanel, Sidebar
from .workers import ExportWorker, LiveDetector, RunAllWorker


class PageStack(QtWidgets.QStackedWidget):
    """The pages, one on show. Its minimum size is that of the page on show,
    not of the largest page (as a plain stacked widget has), so a page
    with wide controls does not make the window wide for every page."""

    def __init__(self):
        super().__init__()
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)
        self.currentChanged.connect(lambda _: self.updateGeometry())

    def minimumSizeHint(self):
        page = self.currentWidget()
        return page.minimumSizeHint() if page is not None             else super().minimumSizeHint()


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — antiproton analysis")
        self.resize(1480, 920)
        self.s = Session()
        self.live = LiveDetector(self.s)
        self._thread = self._worker = None

        # top bar
        bar = self.bar = QtWidgets.QFrame()
        bar.setObjectName("bar")
        hb = QtWidgets.QHBoxLayout(bar)
        hb.setContentsMargins(0, 0, 10, 0)
        hb.setSpacing(0)
        brand = QtWidgets.QLabel(APP_NAME)
        brand.setObjectName("brand")
        glow(brand, radius=14)
        hb.addWidget(brand)
        self.brand = brand
        sub = QtWidgets.QLabel(f"v{__version__}")
        sub.setObjectName("brandsub")
        hb.addWidget(sub)

        # File and Help sit on the same line as the tabs; there is no
        # separate menu bar. Their menus are filled in _menus().
        self.file_btn = self._menu_button("File")
        self.view_btn = self._menu_button("View")
        self.help_btn = self._menu_button("Help")
        hb.addWidget(self.file_btn)
        hb.addWidget(self.view_btn)
        hb.addWidget(self.help_btn)
        hb.addSpacing(14)

        self.pages = make_pages(self.s)
        for page in self.pages:
            page.navigate = self.navigate
        self.stack = PageStack()
        self.nav = QtWidgets.QButtonGroup(self)
        self.nav.setExclusive(True)
        for k, page in enumerate(self.pages):
            self.stack.addWidget(page)
            b = QtWidgets.QPushButton(page.title)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setToolTip(f"{page.hint}   (Ctrl+{k + 1})")
            b.setCursor(QtCore.Qt.PointingHandCursor)
            self.nav.addButton(b, k)
            hb.addWidget(b)
        self.nav.idClicked.connect(self.show_page)
        # a tool button asks for a few pixels more than a tab; keep one line
        for b in (self.file_btn, self.view_btn, self.help_btn):
            b.setFixedHeight(self.nav.button(0).sizeHint().height())
        hb.addStretch(1)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setFixedWidth(160)
        self.progress.hide()
        hb.addWidget(self.progress)
        hb.addSpacing(10)
        self.run_btn = QtWidgets.QPushButton("Run all")
        self.run_btn.setObjectName("primary")
        self.run_btn.setToolTip("Count and measure every image in every "
                                "dataset with the current settings (Ctrl+R)")
        self.run_btn.clicked.connect(self.run_all)
        hb.addWidget(self.run_btn)
        hb.addSpacing(6)
        self.export_btn = QtWidgets.QPushButton("Export…")
        self.export_btn.setToolTip("Write CSVs, marked images and the master "
                                   "archive (Ctrl+E)")
        self.export_btn.clicked.connect(self.export)
        hb.addWidget(self.export_btn)

        # body
        self.sidebar = Sidebar(self.s)
        self.detection = DetectionPanel(self.s)
        self.right = SidePanel(self.detection)
        self.console = Console(self.s)

        centre = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        centre.addWidget(self.sidebar)
        centre.addWidget(self.stack)
        centre.addWidget(self.right)
        centre.setStretchFactor(1, 1)
        centre.setSizes([270, 900, 330])
        centre.setCollapsible(1, False)
        centre.setCollapsible(2, False)    # its arrow folds the panel
        self.list_width = 270              # as the list was last dragged
        centre.splitterMoved.connect(
            lambda *_: setattr(self, "list_width", centre.sizes()[0]))

        vsplit = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vsplit.addWidget(centre)
        vsplit.addWidget(self.console)
        vsplit.setStretchFactor(0, 1)
        vsplit.setSizes([780, 120])

        root = self.backdrop = Backdrop(TUBE)
        v = QtWidgets.QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(bar)
        v.addWidget(vsplit, 1)
        self.setCentralWidget(root)
        # the panels that turn to frosted glass in the Glass theme
        self.frost = Frost(root, [bar, self.sidebar, self.stack,
                                  self.right, self.console])
        self.frost.framed.append(plot_frames(self.stack))
        self.frost.extras.append(self._tab_glow)
        self.popup_glass = PopupGlass(root)       # menus and dialogs
        # the background never drifts while the analysis works
        root.busy = lambda: (self._thread is not None or QtCore.QThreadPool
                             .globalInstance().activeThreadCount() > 0)

        self._shortcuts()
        self._menus()
        st = QtCore.QSettings()
        self.glass_intensity = str(st.value("glass_intensity", "Strong"))
        if self.glass_intensity not in INTENSITIES:
            self.glass_intensity = "Strong"
        self.animate_on = st.value("animate_background", True, type=bool)
        self.set_theme(str(st.value("theme", "Phosphor")), save=False)
        # the settings column at the right: open, or folded to a strip
        self.right.toggled.connect(self.set_settings_panel)
        for page in self.pages:
            if hasattr(page, "side"):
                page.side.toggled.connect(self.set_settings_panel)
        self.set_settings_panel(st.value("settings_panel", True, type=bool),
                                save=False)
        self.s.paramsChanged.connect(self._update_run_button)
        self.s.resultsChanged.connect(self._update_run_button)
        self.s.datasetsChanged.connect(self._update_run_button)
        self._update_run_button()

        self.show_page(0)
        self.s.log(f"{APP_NAME} {__version__} ready. Add a folder of runs "
                   "(Ctrl+O) or drop one on the list.", "ok")

    # navigation
    def show_page(self, k):
        self.nav.button(k).setChecked(True)
        self.bar.update()                         # the tab glow moves
        self.stack.setCurrentIndex(k)
        page = self.pages[k]
        self.right.setVisible(page.uses_detection)
        self.settle_right()
        page.shown()

    def settle_right(self):
        """The settings column at the right as wide as it needs (that
        differs by look, and folded), the list at the left as it was last
        dragged (less if the page needs it), the page in between the rest:
        the same layout every time."""
        centre = self.right.parentWidget()
        if not self.isVisible() or self.right.isHidden():
            return
        right = self.right.sizeHint().width()
        room = centre.width() - 2 * centre.handleWidth()
        left = min(self.list_width,
                   room - right - self.stack.minimumSizeHint().width())
        left = max(left, self.sidebar.minimumSizeHint().width())
        centre.setSizes([left, max(0, room - left - right), right])

    def navigate(self, title, spot=None):
        """Jump to a page by name; optionally centre the image on a spot."""
        k = next(i for i, p in enumerate(self.pages) if p.title == title)
        self.show_page(k)
        if spot is not None and hasattr(self.pages[k], "focus"):
            QtCore.QTimer.singleShot(120, self.pages[k],
                                     lambda: self.pages[k].focus(*spot))

    def _shortcuts(self):
        """Shortcuts with no menu entry. The others belong to the actions in
        _menus(): a key bound twice is ambiguous and Qt then ignores it."""
        def sc(key, fn):
            QtGui.QShortcut(QtGui.QKeySequence(key), self, fn)
        for k in range(len(self.pages)):
            sc(f"Ctrl+{k + 1}", lambda k=k: self.show_page(k))
        sc("Ctrl+R", self.run_all)
        sc("PgDown", lambda: self.sidebar.step(1))
        sc("PgUp", lambda: self.sidebar.step(-1))

    def _menu_button(self, text):
        """A top-bar button that drops a menu, styled like the tabs."""
        b = QtWidgets.QToolButton()
        b.setText(text)
        b.setObjectName("menu")
        b.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        b.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        return b

    def _menus(self):
        def action(menu, text, fn, key=None):
            a = QtGui.QAction(text, self)
            a.triggered.connect(fn)
            if key:
                a.setShortcut(QtGui.QKeySequence(key))
            menu.addAction(a)
            self.addAction(a)        # the shortcut works with the menu closed
            return a

        m = self.file_menu = QtWidgets.QMenu(self)
        action(m, "Add folder…", self.sidebar.pick_folder, "Ctrl+O")
        action(m, "Add images…", self.sidebar.pick_images, "Ctrl+Shift+O")
        m.addSeparator()
        action(m, "Export…", self.export, "Ctrl+E")
        m.addSeparator()
        action(m, "Quit", self.close, "Ctrl+Q")
        self.file_btn.setMenu(m)
        v = self.view_menu = QtWidgets.QMenu(self)
        group = QtGui.QActionGroup(self)
        self.theme_actions = {}
        for name in THEMES:
            a = action(v, f"{name} theme", lambda _=False, n=name:
                       self.set_theme(n))
            a.setCheckable(True)
            group.addAction(a)
            self.theme_actions[name] = a
        v.addSeparator()
        gi = self.intensity_menu = v.addMenu("Glass intensity")
        group = QtGui.QActionGroup(self)
        self.intensity_actions = {}
        for level in INTENSITIES:
            a = action(gi, level, lambda _=False, n=level:
                       self.set_glass_intensity(n))
            a.setCheckable(True)
            group.addAction(a)
            self.intensity_actions[level] = a
        self.animate_action = action(v, "Animate background",
                                     lambda on: self.set_animation(on))
        self.animate_action.setCheckable(True)
        self.panel_action = action(v, "Settings panel",
                                   lambda on: self.set_settings_panel(on))
        self.panel_action.setCheckable(True)
        self.view_btn.setMenu(v)
        h = self.help_menu = QtWidgets.QMenu(self)
        action(h, "Keyboard shortcuts", self._keys)
        action(h, "About", self._about)
        self.help_btn.setMenu(h)

    # look
    def set_theme(self, name, save=True):
        """Switch to the Phosphor or Glass look. Only the look changes: the
        datasets, the current image and the results stay as they are."""
        if name not in THEMES:
            name = "Phosphor"
        self._look(name, self.glass_intensity)
        if save:
            QtCore.QSettings().setValue("theme", name)

    def set_glass_intensity(self, level, save=True):
        """Subtle (frosted, the first Glass look) or Strong (liquid glass).
        Kept for when Glass is on."""
        if level not in INTENSITIES:
            level = "Strong"
        self.glass_intensity = level
        self._look(current(), level)
        if save:
            QtCore.QSettings().setValue("glass_intensity", level)

    def set_settings_panel(self, on, save=True):
        """Show the settings column at the right (image, spots, ions), or
        fold it to a thin strip to give the picture the room."""
        on = bool(on)
        self.panel_action.setChecked(on)
        for panel in [self.right] + [p.side for p in self.pages
                                     if hasattr(p, "side")]:
            panel.blockSignals(True)
            panel.set_open(on)
            panel.blockSignals(False)
        if save:
            QtCore.QSettings().setValue("settings_panel", on)

    def set_animation(self, on, save=True):
        """Let the Strong background drift (never when the system asks for
        reduced motion)."""
        self.animate_on = bool(on)
        self.animate_action.setChecked(self.animate_on)
        self.backdrop.animate(self.animate_on and not reduced_motion())
        if save:
            QtCore.QSettings().setValue("animate_background", self.animate_on)

    def _look(self, name, level):
        glass = name == "Glass"
        strong = glass and level == "Strong"
        was_muted = muted()
        if name != current() or (glass and level != intensity()):
            use_theme(name, glass_intensity=level)
        elif level != intensity():
            set_intensity(level)                  # Phosphor: nothing to redraw
        self.backdrop.glass = glass
        self.backdrop.intensity = level
        self.popup_glass.set_on(strong)
        pad = glass_ui.S_INSET + 6 if strong else 6 if glass else 0
        # room inside the rounded edge (a stacked widget ignores its own
        # margins: its pages get them)
        boxes = [w for w in self.frost.widgets if w is not self.stack] +             [self.stack.widget(k) for k in range(self.stack.count())]
        for w in boxes:
            lay = w.layout()
            if lay is not None:
                if not hasattr(w, "_margins"):
                    w._margins = lay.contentsMargins()
                m = w._margins
                lay.setContentsMargins(m.left() + pad, m.top() + pad,
                                       m.right() + pad, m.bottom() + pad)
        # the settings column takes the width this look needs from the page
        # beside it, never from the list: back in a look, the same layout
        self.right._size_area()
        self.settle_right()
        restyle_plots(self)
        self.console.inset(glass_ui.S_INSET + 4 if strong else 0,
                           4 if strong else 10 if glass else 4)
        if muted() != was_muted:                  # text drawn in code
            self.console.restyle()
            self.sidebar.update_counts()
            for page in self.pages:
                page.mark()
        self.theme_actions[name].setChecked(True)
        self.intensity_actions[level].setChecked(True)
        self.animate_action.setChecked(self.animate_on)
        self.backdrop.animate(self.animate_on and not reduced_motion())
        if self.isVisible():
            windows_frame(self, glass)
        self.update()

    def _tab_glow(self, w, p):
        """Strong glass: a soft phosphor glow under the selected tab."""
        b = self.nav.checkedButton()
        if w is not self.bar or b is None:
            return
        g = b.geometry()
        p.save()
        p.translate(g.center().x(), g.bottom() - 1)
        p.scale(g.width() * 0.55, 14)
        glow_ = QtGui.QRadialGradient(0, 0, 1)
        c = QtGui.QColor(PHOSPHOR)
        c.setAlpha(110)
        glow_.setColorAt(0, c)
        c.setAlpha(0)
        glow_.setColorAt(1, c)
        p.fillRect(QtCore.QRectF(-1, -1, 2, 1), glow_)
        p.restore()

    def _keys(self):
        QtWidgets.QMessageBox.information(self, "Keyboard shortcuts",
            "Ctrl+1 … Ctrl+8    switch analysis\n"
            "PgUp / PgDn        previous / next image\n"
            "↑ / ↓              move in the run list\n"
            "Ctrl+O             add a folder\n"
            "Ctrl+Shift+O       add images\n"
            "Ctrl+R             run all\n"
            "Ctrl+E             export\n"
            "Ctrl+Q             quit")

    def _about(self):
        """Everything shown comes from dipesh/_about.py."""
        rows = "".join(f"<tr><td style='color:{muted()}; padding-right:14px'>"
                       f"{label}</td><td>{text}</td></tr>"
                       for label, text in _about.about_lines())
        QtWidgets.QMessageBox.about(self, f"About {_about.NAME}",
            f"<p><b>{_about.TITLE}</b></p><p>{_about.DESCRIPTION}</p>"
            f"<table>{rows}</table>")

    # running
    def _update_run_button(self):
        busy = self._thread is not None
        has = any(d.items for d in self.s.datasets)
        self.run_btn.setEnabled(has and not busy)
        stale = self.s.stale
        self.run_btn.setObjectName("stale" if stale else "primary")
        self.run_btn.setText("Run all again" if stale else "Run all")
        self.run_btn.setToolTip(
            "The settings changed since the last run — counts in the list "
            "are out of date" if stale else
            "Count and measure every image in every dataset (Ctrl+R)")
        self.run_btn.style().unpolish(self.run_btn)
        self.run_btn.style().polish(self.run_btn)
        self.export_btn.setEnabled(not busy and
                                   any(d.done() for d in self.s.datasets))

    def run_all(self):
        if self._thread is not None:
            return
        jobs = self.s.all_items()
        if not jobs:
            return
        params = self.s.params
        for d in self.s.datasets:
            d.results.clear()
        self.s.results_params = params
        self.s.resultsChanged.emit()
        self.s.log(f"run all: {len(jobs)} images in "
                   f"{len(self.s.datasets)} datasets")
        self.progress.setRange(0, len(jobs))
        self.progress.setValue(0)
        self.progress.show()

        self._thread = QtCore.QThread(self)
        self._worker = RunAllWorker(jobs, params, self.s.pickup)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        # the worker emits from its own thread: every receiver is a bound
        # slot of this window, delivered through the GUI thread's event loop.
        # (A lambda here is called in the worker thread and crashes Qt. So
        # is a slot overridden in a Python subclass: do not subclass these.)
        queued = QtCore.Qt.QueuedConnection
        self._worker.one.connect(self._one_done, queued)
        self._worker.progress.connect(self._on_run_progress, queued)
        self._worker.finished.connect(self._run_finished, queued)
        self._thread.start()
        self._update_run_button()

    @QtCore.Slot(int, int)
    def _on_run_progress(self, i, n):
        self.progress.setValue(i)

    @QtCore.Slot(object, object)
    def _one_done(self, ds, r):
        ds.results[r.item.key] = r
        if not r.ok:
            self.s.log(f"{ds.name}/{r.item.name}: {r.error}", "error")
        # repaint in batches, not on every image
        if len(ds.results) % 8 == 0:
            self.s.resultsChanged.emit()

    @QtCore.Slot(float, int, int)
    def _run_finished(self, secs, n_ok, n_bad):
        self._thread.quit()
        self._thread.wait()
        self._thread = self._worker = None
        self.progress.hide()
        total = sum(r.n for d in self.s.datasets for r in d.done())
        self.s.log(f"counted {n_ok} images in {secs:.1f} s — {total} "
                   f"antiprotons" + (f", {n_bad} failed" if n_bad else ""),
                   "ok" if not n_bad else "warn")
        self.s.resultsChanged.emit()
        self._update_run_button()

    def export(self):
        if self._thread is not None:
            return
        results = self.s.results()
        if not any(results.values()):
            self.s.log("nothing to export yet — run all first", "warn")
            return
        dlg = ExportDialog(self, self.s)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        out, marked, master, replace = dlg.values()
        self.s.log(f"exporting to {out}")
        self.progress.setRange(0, 0)
        self.progress.show()
        self._thread = QtCore.QThread(self)
        self._worker = ExportWorker(results, out, self.s.results_params or
                                    self.s.params, marked, master, replace)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        queued = QtCore.Qt.QueuedConnection
        self._worker.progress.connect(self._on_export_progress, queued)
        self._worker.finished.connect(self._export_finished, queued)
        self._thread.start()
        self._update_run_button()

    @QtCore.Slot(int, int)
    def _on_export_progress(self, i, n):
        self.progress.setRange(0, n)
        self.progress.setValue(i)

    @QtCore.Slot(bool, str)
    def _export_finished(self, ok, msg):
        self._thread.quit()
        self._thread.wait()
        self._thread = self._worker = None
        self.progress.hide()
        self.s.log(msg, "ok" if ok else "error")
        self._update_run_button()

    def closeEvent(self, e):
        if self._worker is not None and hasattr(self._worker, "cancel"):
            self._worker.cancel()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(5000)
        for page in self.pages:                   # pages with their own work
            if hasattr(page, "stop"):
                page.stop()
        self.backdrop.animate(False)              # no drift, no app-wide
        self.popup_glass.set_on(False)            # event watching when closed
        e.accept()

    def showEvent(self, e):
        super().showEvent(e)
        windows_frame(self, self.backdrop.glass)
        strong = self.backdrop.strong             # back after a close
        self.popup_glass.set_on(strong)
        self.backdrop.animate(self.animate_on and strong and not reduced_motion())
