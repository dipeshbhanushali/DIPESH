# Changes

## 2.0.0 (in development)

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
