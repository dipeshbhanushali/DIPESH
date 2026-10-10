# learn / spots — the lesson texts

Edit freely while the program runs: every time this file is saved, the text
on screen is read again.

The format is the one of image.md: `## key`, then `title:`, `shown:`,
`legend:` lines, then the explanation in Markdown with live values in braces.
{about} is replaced by the feature's definition from features.md.

The keys are the columns of the spot table (spot, x, y, luminosity,
radius_used, area, peak, sum5x5, radial_sigma, concentration, eccentricity,
profile_slope, nn_dist, is_isolated), the controls above it (scope, iso_only,
info, save), the detection panel (panel) and the introduction (intro).

Live values: {run} {x} {y} {peak} {sum5x5} {spread} {luminosity}
{radius_used} {area} {radial_sigma} {concentration} {concentration_pct}
{eccentricity} {profile_slope} {decay_px} {nn_dist} {is_isolated} {iso_r}
{isolation_factor} {spot_max_radius} {plateau_pct} {bg_res} {gx} {gy}
{core_light} {total_light} {axis_long} {axis_short} {growth} {n_rows}
{scope} {iso_only}

## intro
title: spots — what is measured on each spot
shown: the background-subtracted image around the spot
legend: white circle = the spot's aperture (amber when the spot is crowded)
legend: green plus = the spot's peak pixel

The table above is the spots page: one row per spot, one column per
measurement. Under it, **the spot** shows one spot zoomed in, and **radial
profile** shows how its light falls off from its centre.

Rest the mouse on a column header: the figures show what that column
measures, on the spot shown, and this text explains it. Rest the mouse on a
cell: the figures move to that row's spot. Click a row to keep its spot on
show.

The spots come from learn's own detection settings, on the right; they reach
the analysis only with **Apply**.

**In the figures**, the circle is the aperture over which the spot's light
was summed, white for an isolated spot and amber for a crowded one; the
green plus marks the peak pixel.

## panel
title: detection settings
shown: the background-subtracted image around the spot
legend: white circle = the spot's aperture (amber when the spot is crowded)

These are learn's detection settings. They decide which spots are found,
so which rows the table holds, and the spot measurement settings decide
the aperture each spot is measured in. Every setting is explained in
learn / image.

Moving a setting re-detects the image: the table and the figures follow.

## scope
title: spots from: {scope}
shown: the background-subtracted image around the spot

The spot table can list two sets of spots:

- **this image (live settings)**: the spots of the image selected in the
  list on the left, detected again whenever a setting moves;
- **whole dataset (last run all)**: every spot of every image of the
  selected dataset, as measured by the last **Run all**. The first column
  then names the image and the spot.

On show now: {scope}, {n_rows} rows.

## iso_only
title: isolated only: {iso_only}
shown: the background-subtracted image around the spot

- With **isolated only** switched on, the table lists only the isolated
  spots, those whose aperture holds their own light alone.
- With **isolated only** switched off, the table lists every spot.

It is switched {iso_only} now: {n_rows} rows.

## info
title: the count of the table
shown: the background-subtracted image around the spot

The number of spots in the table, and how many of them are isolated.

## save
title: save as CSV
shown: the background-subtracted image around the spot

**Save as CSV…** writes the rows of the table, as they are listed now, to a
file of comma-separated values, one line per spot, which a spreadsheet can
open.

## spot
title: spot {run} ({x}, {y})
shown: the background-subtracted image around the spot
legend: white circle = the spot's aperture (amber when the spot is crowded)
legend: green plus = the spot's peak pixel

The first column numbers the spots of the image, brightest peak first; for a
whole dataset it names the image and the number.

**In the figures**, the green plus marks the peak pixel at ({x}, {y}), and
the circle is the aperture.

## x
title: x = {x}
shown: the background-subtracted image around the spot
legend: green plus = the spot's peak pixel

x is the column of the spot's peak pixel in the image, counted from the
left edge, in pixels.

**In the figures**, the green plus marks the peak pixel.

## y
title: y = {y}
shown: the background-subtracted image around the spot
legend: green plus = the spot's peak pixel

y is the row of the spot's peak pixel in the image, counted from the top
edge, in pixels.

**In the figures**, the green plus marks the peak pixel.

## luminosity
title: luminosity = {luminosity}
shown: the background-subtracted image around the spot
legend: amber fill = a pixel inside the aperture, summed into the luminosity
legend: white circle = the aperture, radius {radius_used} px

{about}

This spot: {area} pixels inside the aperture, a residual background of
{bg_res} per pixel, a luminosity of {luminosity}.

**In the figures**, the amber pixels are the pixels inside the aperture, the
ones summed into the luminosity, and the white circle is the aperture's edge.

## radius_used
title: aperture radius = {radius_used} px
shown: the background-subtracted image around the spot
legend: white circle = the aperture the spot grew to, {radius_used} px
legend: white dashed circle = a ring the aperture grew through
legend: amber dashed circle = the max aperture, {spot_max_radius} px

{about}

This spot grew ring by ring; it stops when a ring adds less than
{plateau_pct} % of the light already inside:

{growth}

**In the figures**, the thin dashed white circles are the rings the
aperture grew through, the solid white circle is the aperture it stopped at,
and the dashed amber circle is the max aperture it could not pass.

## area
title: aperture area = {area} px
shown: the background-subtracted image around the spot
legend: amber fill = a pixel inside the aperture, counted in the area
legend: white circle = the aperture, radius {radius_used} px

{about}

This spot: radius {radius_used} px, {area} pixels.

**In the figures**, the amber pixels are the pixels counted in the area.

## peak
title: peak = {peak}
shown: the background-subtracted image around the spot
legend: white box = the peak pixel

{about}

This spot's peak pixel is at ({x}, {y}), with a value of {peak}.

**In the figures**, the white box marks the peak pixel.

## sum5x5
title: 5x5 sum = {sum5x5}
shown: the background-subtracted image around the spot
legend: amber box = the 5 × 5 box whose pixels are summed
legend: white box = the peak pixel, the centre of the box

{about}

This spot: 5x5 sum {sum5x5}, peak {peak}, so a spread (5x5 sum / peak) of
{spread}.

**In the figures**, the amber box holds the 25 summed pixels and the white
box marks the peak pixel at its centre.

## radial_sigma
title: radial σ = {radial_sigma} px
shown: the background-subtracted image around the spot; the radial profile
legend: green plus = the centroid, the light-weighted centre
legend: white circle = a circle of radius radial σ around the centroid
legend: amber dashed circle = the aperture
legend: white line = radial σ on the profile

{about}

This spot: centroid at ({gx}, {gy}), radial σ {radial_sigma} px.

**In the figures**, the green plus is the centroid and the white circle
around it has the radius radial σ: most of the light lies inside it. On the
radial profile, the white line marks the same distance.

## concentration
title: concentration = {concentration}
shown: the background-subtracted image around the spot; the radial profile
legend: amber fill = a pixel within 2 px of the centroid, the core
legend: green plus = the centroid
legend: white circle = the aperture
legend: amber dashed line = 2 px from the centroid, on the profile

{about}

This spot: {core_light} of its {total_light} light lies in the core, a
concentration of {concentration} ({concentration_pct} %).

**In the figures**, the amber pixels are the core, within 2 px of the green
plus, the centroid; the white circle is the whole aperture. On the radial
profile, the dashed amber line marks 2 px: the points to its left are the
core.

## eccentricity
title: eccentricity = {eccentricity}
shown: the background-subtracted image around the spot
legend: amber circle = the 2σ ellipse of the spot's light
legend: amber line = the ellipse's long axis
legend: white dashed circle = the aperture

{about}

This spot: spread of the light along the long axis {axis_long} px, along
the short axis {axis_short} px (as standard deviations), so an eccentricity
of {eccentricity}.

**In the figures**, the amber ellipse encloses the spot's light out to two
standard deviations along each axis, and the amber line is its long axis.
A round spot draws a circle; an elongated spot draws a long ellipse.

## profile_slope
title: profile slope = {profile_slope}
shown: the radial profile: log light per pixel against distance from the centroid
legend: green dot = an aperture pixel: its log light against its distance from the centroid
legend: amber line = the straight-line fit; its slope is the profile slope
legend: green plus = the centroid, in the spot window

{about}

This spot: slope {profile_slope} per pixel, so its light falls by a factor
e (2.7) every {decay_px} px.

**In the radial profile**, each green dot is one pixel of the aperture, and
the amber line is the straight line fitted through them; the profile slope
is the slope of that line.

## nn_dist
title: nearest-neighbour distance = {nn_dist} px
shown: the background-subtracted image around the spot
legend: white circle = the spot's aperture
legend: red ring = the nearest other spot
legend: red dashed line = the distance measured

{about}

This spot: nearest neighbour at {nn_dist} px.

**In the figures**, the red ring is the nearest other spot and the red
dashed line is the distance measured; a neighbour further than the window
lies along the line, outside it.

## is_isolated
title: isolated: this spot is {is_isolated}
shown: the background-subtracted image around the spot
legend: white circle = the spot's aperture
legend: white dashed circle = the isolation circle (amber when the spot is crowded)
legend: red ring = the nearest other spot
legend: red dashed line = the distance to it

{about}

This spot: isolation circle {isolation_factor} × {radius_used} px = {iso_r}
px, nearest neighbour {nn_dist} px, so the spot is **{is_isolated}**.

**In the figures**, the dashed circle is the isolation circle; the spot is
isolated when the red ring, its nearest neighbour, lies outside it.
