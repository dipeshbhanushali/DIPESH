# `python -m dipesh` and the packaged build both start here.
# Absolute import on purpose: PyInstaller runs this file as a top-level
# script, where a relative import fails.
from dipesh.graphical_interface.app import main

raise SystemExit(main())
