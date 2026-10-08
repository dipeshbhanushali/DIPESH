# PyInstaller spec for DIPESH.
#
#   pip install .            (a normal install - NOT "pip install -e .";
#                             PyInstaller cannot collect an editable install)
#   pip install pyinstaller
#   pyinstaller build/dipesh.spec --noconfirm --clean
#
# Produces dist/DIPESH/ - the program and its libraries. "onedir" on
# purpose: a single-file Qt build unpacks ~250 MB to a temp folder on every
# launch, which is slow and trips antivirus. build/installer.iss turns the
# folder into a Windows installer.
#
# Run this ON WINDOWS - PyInstaller does not cross-compile.
#
# There is no bytecode encryption (PyInstaller removed it in 6.0: the key has
# to ship inside the program for it to run). An installed app is a
# convenience, not a way to keep the source private.

a = Analysis(
    ['../dipesh/__main__.py'],
    pathex=['..'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'dipesh.graphical_interface.app',
        'dipesh.graphical_interface.main_window',
        'dipesh.graphical_interface.pages',
        'scipy.signal', 'scipy.optimize',
        'matplotlib.backends.backend_agg',
    ],
    hookspath=[],
    runtime_hooks=[],
    # PySide6 ships far more than the widgets we use; leaving the rest out
    # takes hundreds of MB off the build. scipy is NOT excluded: the RF
    # notch and the fits need it.
    excludes=[
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineQuick', 'PySide6.QtWebView',
        'PySide6.QtQuick', 'PySide6.QtQuick3D', 'PySide6.QtQml',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DExtras',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtPositioning',
        'PySide6.QtSerialPort', 'PySide6.QtSql', 'PySide6.QtTest',
        'PySide6.QtDesigner', 'PySide6.QtHelp',
        'PyQt5', 'PyQt6', 'PySide2', 'wx', 'tkinter',
        'IPython', 'jupyter', 'notebook', 'pandas', 'pytest', 'sphinx',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='DIPESH',
    debug=False,
    strip=False,
    upx=False,               # UPX makes antivirus far more jumpy
    console=False,           # no console window behind the app
    icon=None,               # put an .ico path here if you make one
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
               name='DIPESH')
