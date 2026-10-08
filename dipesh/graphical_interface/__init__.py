"""
The desktop app (PySide6 + pyqtgraph). Nothing in here computes anything: it
shows what the analysis packages return. Qt is imported only in this package.

    theme        colours, style sheet, plot styling
    session      datasets, current image, settings, results
    workers      background threads (live detection, run all, export, pickup)
    widgets      detection panel, dataset list, console, export dialog
    main_window  MainWindow
    app          main()
    pages/       one file per analysis on the top bar
"""
