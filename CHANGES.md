# Changes

## 2.0.0 (2026-10-27)

- Ion analysis (`dipesh.ion_analysis`, the *ions* page): MCP release videos,
  single ions counted one by one in a region, a pile-up disc estimated from
  its light with a single-ion calibration (several methods side by side),
  background from the darkest / random / all frames or a separate video,
  frames left out of totals, storage times read from file names (only with a
  unit), an error table per dataset, the decay fit with storage time and
  two-point tau, CSV/JSON export. Every value is a setting. Named "legacy"
  presets repeat earlier analyses; tests show they give exactly the earlier
  numbers on the real videos.
- `find_spots()`, the spot finder, is shared by `detect()` (unchanged) and
  the ion analysis.
- Any image, any folder. JPG/JPEG and BMP are read, as well as TIFF and PNG;
  colour images become grey (BT.601 weights, alpha dropped). Each page of a
  multi-page TIFF and each frame of an AVI or MP4 video is one item; video
  frames are read only when needed, and a frame range can be chosen. A folder
  is read at any depth: each folder of runs or loose files becomes a dataset.
- Nothing is dropped silently: scan() lists every file it skips and why, the
  app logs a line per skipped file, and the summary says how many.
- Floating-point images have a defined rule (README, "Colour and bit depth").
  Integer images give exactly the 1.0 numbers.
- Two themes, chosen in View and remembered: Phosphor (the 1.0 look, the
  default) and Glass (frosted panels over a dark backdrop with a soft
  green/teal glow; plots stay opaque; text contrast at least WCAG AA). On
  Windows 11, Glass also asks for the Mica frame and a dark title bar.
- Glass got two intensities: Strong (new default) is liquid glass over
  slowly drifting colour blobs, with glass controls, menus and dialogs and
  framed plots; Subtle is the first Glass look. The drift can be turned off
  and follows the system's reduced-motion setting. Phosphor is unchanged,
  pixel for pixel (tested against pictures made before the change).
- `docs/make_screenshots.py` writes a screenshot of every page in each look.
- The learn package moved to `graphical_interface/learn/` (it uses Qt). Its
  lessons now call the analysis's own functions (`candidates()`,
  `suppress()`, `second_moments()`, `profile_fit()`) instead of copies, and a
  test pins them to `detect()` and the stored numbers.
- The learn page no longer keeps the window wide after it was shown wide.
- A colour image that is not grey gives slightly different numbers than in
  1.0, which let the file decoder make it grey: the weights are now the same
  for every format.
- The window fits a 1536 x 864 screen (1920 x 1080 at 125 %): the settings
  column scrolls and folds away (its arrow, or View > Settings panel,
  remembered), the list on the left can be made narrow, and a page no longer
  makes the window as wide as the widest page. Tested in every look.
- learn's overview lists the ions page.
- Works with PySide6 6.12, which the Windows build now gets: the number
  boxes beside the sliders were empty with it.
- Version 2.0.0 in the build files and the installer name.

### Known limitations

- **Ion analysis: settings are not yet checked against the physics.** The
  code reproduces the earlier analyses exactly with their presets, but which
  settings and error components are right for a given set of videos is not
  decided by the program (see the open questions in the ion review).
- **The earlier ion numbers depend on NumPy 1.x.** The legacy presets copy
  NumPy 1.x's order for equally bright candidates in pure Python, which is
  slow on frames with thousands of candidates. New analyses use reading
  order.
- **Ion analysis speed.** About 20-40 ms per frame: a 900-frame video takes
  about half a minute, plus the background.
- **Glass looks are drawn by Qt, not by the system**, except the Windows 11
  Mica frame; on other systems Glass is the same without it.
- **The installer is not code-signed**: Windows shows a SmartScreen warning
  at the first start.
- **With PySide6 6.12 the value in a number box sits against its left
  edge** (6.11 leaves a small margin). The Phosphor pixel tests compare
  against pictures made with 6.11.2 and skip themselves with another Qt.
- **The 1.0 limitations below still apply** (concentration of a spot centred
  on a pixel, display arithmetic in the window code).

## 1.0.0 — first public release (2026-10-08)

- Counts antiprotons in MCP / phosphor-screen camera images: hot-pixel
  removal, background subtraction, thresholding, one count per particle.
- Measures every spot: luminosity, area, radial sigma, concentration,
  eccentricity, profile slope, isolation; and per image the integrated light
  and a count from light.
- Compares datasets (histograms with separation score and best cut, PCA) and
  plots any run quantity against any run parameter, with averaging and fits.
- Analyses the PicoScope pickup signals of the same runs: two scopes on one
  clock, trap RF removed with a zero-phase notch, pulse time and size.
- Desktop app with live detection, Run all and Export (CSV files, marked
  images, a growing master archive); the same analysis is importable from
  Python without Qt.
- Tested: each spot feature against its analytic value on synthetic spots,
  six synthetic reference frames against stored numbers, and the window
  itself. `report/make_report.py` writes a LaTeX report of a test run.

### Known limitations

- **Concentration of a spot centred exactly on a pixel.** Concentration is
  the light on the pixels within 2 px of the spot's centre. When the centre
  falls exactly on a pixel, four pixels sit at exactly 2 px and rounding
  decides which of them count, so the value can come out about 10 % low
  (0.35 instead of 0.40 for a spot of sigma 2 px). Real spots are rarely
  centred like that, but it makes concentration a little noisier than the
  other shape features.
- **Some display arithmetic is still in the window code.** The stretch of the
  image brightness, the binning of the histogram, the log axes, the scaling of
  the stacked scope traces and the choice of the default x axis are computed
  in `graphical_interface/pages/`. They only decide how things are drawn; no
  count or measured value comes from them.
