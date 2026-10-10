# learn / image — the lesson texts

Edit freely while the program runs: every time this file is saved, the text
on screen is read again; the next hover shows the change.

How the file is read:

- Each topic starts with a line `## key`. The key says which part of the
  right-hand panel the text belongs to; keep the keys as they are.
- The first lines of a topic are `title:` (the heading above the text),
  `shown:` (which image the two windows show) and any number of `legend:`
  lines: the legend under the two windows, one line per mark, written
  `legend: amber fill = what the amber pixels are`. The mark is a colour
  (amber, white, red, green) and a shape (fill, box, dashed box, circle,
  dashed circle, x, ring, line, dashed line, dot, plus); its icon is drawn
  the way the windows draw it. A legend line without `=` is shown as a plain note.
- Everything after them, up to the next `## `, is the explanation, in
  Markdown: **bold**, *italic*, lists, `> ` for an indented line.
- A word in braces, like {n} or {thresh}, is replaced by the live number of
  the current frame. The names you can use are listed at the end of this
  file. A name that has no value on this frame shows as "–".
- Everything above the first `## ` (this part) is never shown.

## intro
title: image — what the detection computes
shown: the camera image
legend: white circle = an isolated spot, at the aperture its light was summed over
legend: amber circle = a crowded spot, at the aperture its light was summed over

The two windows on the left are zoomed in on the frame you selected.
**event** is centred on one detected spot; **background** on a patch of the
same frame with no spot in it. Every pixel is a camera pixel.

Rest the mouse on any number or setting in the panel on the right. The
windows then show what it acts on and this text explains it, with the
numbers of this frame. Move a slider and the count, the windows and the
table all follow.

The settings here are learn's own, to try things out: the image page and
Run all keep theirs until you press **Apply**. They start from the
analysis's settings.

The table above lists what the program measured for the event. Use ◀ ▶ to
step through the spots, the most isolated spot first.

**In the windows**, each circle is a spot the program counted, drawn at
the aperture its light was summed over: white for an isolated spot, amber
for a crowded one. The background window should hold no circle.

## count
title: {n} antiprotons in this run
shown: the camera image
legend: white circle = an isolated spot, at the aperture its light was summed over
legend: amber circle = a crowded spot, at the aperture its light was summed over
legend: red x = a pixel that passed every cut but lies within min separation of a brighter spot

The count is the number of spots that are identified as events: they pass every detection cut on this
frame. 

Candidates are accepted if they are bright enough and light up a few pixels nearby.

**In the windows**, each circle is a counted spot, white when the spot is
isolated and amber when the spot is crowded. A red ✕ marks a pixel that
passed every cut but was dropped because a brighter spot is closer than the
min separation; most red ✕ sit on the flat top of the spot itself.

## sigma
title: noise σ = {sigma}
shown: the image after a first plain blur is subtracted (the residual r)
legend: amber fill = a pixel brighter than {mask_nsigma} σ, left out of the second background pass

The noise of the frame, measured on the residual r = image − blurred image:

> σ = 1.4826 × median(|r − median(r)|)

The median makes it robust: the few bright spot pixels hardly move it, where
a standard deviation would be pulled up by them. The factor 1.4826 makes it
equal to the standard deviation for Gaussian noise.

σ is used twice. Pixels above {mask_nsigma} σ ({mask_level} on the 0-255
scale) are hidden from the second background pass, so a spot does not raise
its own baseline. And with adaptive thresholding switched on, the peak must
clear noise multiple × σ = {nsig}.

**In the windows**, an amber pixel is brighter than {mask_nsigma} σ in the
residual and is left out of the second background pass. In the event window
the amber pixels cover the spot ({masked_ev} pixels), which is why the spot
does not raise its own background. In the background window only noise can
reach {mask_nsigma} σ: {masked_bg} pixels.

## thresh
title: threshold used = {thresh}
shown: the background-subtracted image
legend: amber fill = a pixel above the threshold used ({thresh})
legend: white box = the event's peak pixel

The threshold used is the cut every spot's peak must clear, on the
background-subtracted image, 0-255 scale. How the threshold used is chosen:

- with adaptive thresholding **on**, the threshold used is the larger of the
  peak threshold and noise multiple × σ;
- with adaptive thresholding **off**, the threshold used is the peak
  threshold.

{thresh_rule}

This event's peak, {ev_peak}, {pass_peak} the cut.

**In the windows**, every pixel above the threshold used is coloured amber,
and a white box marks the event's peak pixel. In the background window no
pixel should be amber: one that is would be noise passing the cut. Amber
pixels in this background window: {above_bg}.

## hot
title: hot pixels fixed = {n_hot}
shown: the camera image before the hot-pixel fix
legend: red box = a hot pixel, replaced by the median of its 3 × 3 neighbourhood

A hot pixel is a single camera pixel much brighter than the pixels around
it: a defect or a cosmic ray, not a particle that should be detected.

Hot pixels are discarded with a median filter. Every
pixel more than **hot-pixel delta** ({hotpix_delta}) above the median of its
3 × 3 neighbourhood is replaced by that median.

A real spot spreads its light over many pixels, so its centre is close to
the median of its neighbours and is left alone.

Replaced on this frame: {n_hot}. In the event window: {hot_ev}; in the
background window: {hot_bg}.

**In the windows**, a red box marks each pixel that was replaced as hot.
Most frames have only a few hot pixels, so the windows often show none.

## iso
title: isolated spots = {n_iso} of {n}
shown: the camera image
legend: white circle = the event's aperture
legend: white dashed circle = the isolation circle (amber when the event is crowded)
legend: red ring = a neighbouring spot
legend: red dashed line = the way to the nearest neighbour

A spot is **isolated** when its nearest neighbour is far away. It we call the distace in pixel R the program check the condition 

R > isolation factor × r

where r is its own aperture radius. Only under this condition all the light in
an event belong to it alone and do not mix its information with its neighbour's light.

This event: aperture radius {ev_r} px, isolation circle {isolation_factor} ×
{ev_r} = {iso_r} px, nearest neighbour {ev_nn} → this event is
**{ev_iso}**.

On the image page isolated spots are drawn white, crowded ones amber.

**In the event window**, the solid white circle is the event's aperture
and the dashed circle is the isolation circle, isolation factor × the
aperture radius. The dashed circle is white when the event is isolated and
amber when it is crowded. A red ring marks a neighbouring spot, and the red
dotted line points to the nearest neighbour, which can lie outside the
window.

## lum
title: count from light = {lum_count}
shown: the background-subtracted image
legend: white circle = the fixed aperture of {aperture_radius} px, the light of one spot

The count from light is a second count, independent of the spot finder: all
the light inside the MCP circle (the MCP, microchannel plate, is the
detector; the circle is its active area), divided by the light of an
average spot.

> count from light = integrated light / (sum over spots of their light in a
> {aperture_radius} px aperture / number of spots)

The background-subtracted image is clipped at zero, so its noise floor has a
small positive mean, {bg_res} per pixel on this frame. It is subtracted from
every pixel before summing.

When two spots overlap the finder counts one, but their light still adds up,
so this number goes on growing. On a frame with well-separated spots the two
counts agree: here {n} and {lum_count}.

**In the event window**, the white circle is the fixed aperture of
{aperture_radius} px in which each spot's light is measured for the average
spot. The background window shows the light left after subtraction, whose
mean {bg_res} per pixel is removed before summing.

## detection
title: detection
shown: the camera image
legend: white circle = an isolated spot, at the aperture its light was summed over
legend: amber circle = a crowded spot, at the aperture its light was summed over

These settings decide **which spots are counted**. Each one is a cut, or a
step that prepares the image for the cuts. Rest on any of them to see what
it does.

## measurement
title: spot measurement
shown: the camera image
legend: white circle = an isolated spot, at the aperture its light was summed over
legend: amber circle = a crowded spot, at the aperture its light was summed over

These settings decide **how each counted spot is measured**: its aperture,
and whether it is isolated. They never change the count.

## abs_thresh
title: peak threshold = {abs_thresh}
shown: the background-subtracted image
legend: amber fill = a pixel above the peak threshold ({abs_thresh})
legend: white box = the event's peak pixel

The peak threshold is the main control. The brightest pixel of a spot, in
the background-subtracted image, must be above the peak threshold.

Any bit depth is renormalized to 0-255 for consistency. This is not a
renormalization by the maximum luminosity in the image, but a
renormalization by the maximum luminosity that an image can potentially
have.

This event's peak, {ev_peak}, {pass_abs} the peak threshold.

{abs_note}

**In the windows**, every pixel brighter than the peak threshold is coloured
amber, and a white box marks the event's peak pixel. In the background
window no pixel should be amber: one that is would be noise passing the
cut.

## n_sigma
title: noise multiple = {n_sigma}
shown: the background-subtracted image
legend: amber fill = a pixel above noise multiple × σ ({nsig})
legend: white box = the event's peak pixel

The noise multiple matters only with adaptive thresholding:

- with adaptive thresholding **on**, a peak must also clear noise multiple
  times the noise of the frame: {n_sigma} × {sigma} = {nsig}. A noisy frame
  then gets a stricter cut by itself, without changing the peak threshold.
  The threshold used is the larger of the peak threshold and noise multiple
  × σ;
- with adaptive thresholding **off**, the noise multiple is not used.

{thresh_rule}

**In the windows**, every pixel above noise multiple × σ = {nsig} is
coloured amber, and a white box marks the event's peak pixel. Raise the
noise multiple and the amber shrinks to the brightest core of the spot.

## sum_thresh
title: 5x5 sum min = {sum_thresh}
shown: the background-subtracted image
legend: amber box = the 5 × 5 box whose light is summed
legend: white box = the event's peak pixel, the centre of the 5 × 5 box

The light summed over the 5 × 5 box centred on the peak pixel must be more
than the 5x5 sum min. This cut rejects flickers that have one bright pixel
but little light in total.

This event's 5x5 sum, {ev_sum5}, {pass_sum} the cut.

**In the event window**, the amber box is the 5 × 5 box centred on the
peak pixel, which is marked by the white box. The 5x5 sum is the light of
the 25 pixels inside the amber box.

## spread_min
title: spread min = {spread_min}
shown: the background-subtracted image
legend: amber box = the 5 × 5 box whose light is summed
legend: white box = the event's peak pixel

spread = 5x5 sum / peak: how many pixels' worth of light the 5 × 5 box
holds, compared with the brightest pixel.

A real spot spreads its light over several pixels and has a large spread. A
single bright pixel that survived the hot-pixel fix has a spread close to 1:
its 5 × 5 box holds hardly more than the pixel itself.

This event's spread, {ev_sum5} / {ev_peak} = {ev_spread}, {pass_spread} the cut.

**In the event window**, the white box is the peak pixel and the amber box
is the 5 × 5 box around it. The spread compares the light in the amber box
with the light of the white box alone.

## min_dist
title: min separation = {min_dist} px
shown: the background-subtracted image
legend: amber circle = the min separation around the event
legend: amber dashed circle = the min separation around another spot
legend: red x = a pixel that passed every cut but was dropped inside a brighter spot's circle

One particle can light up a few neighbouring local maxima. Candidates are
taken brightest first, and every other candidate closer than the min
separation to an accepted spot is dropped, so the particle is counted once.

If the min separation is too small, one particle is counted twice; if the
min separation is too large, two real particles close together are counted
as one.

Pixels that passed every cut but were dropped on this frame:
{n_suppressed}. Most of them are not other particles: the top of a spot is
flat to within one count, so several of its pixels qualify as a maximum and
only the brightest is kept.

**In the windows**, the solid amber circle has the radius of the min
separation around the event; dashed amber circles are the same around the
other spots. A red ✕ marks a pixel that passed every cut but lies inside the
circle of a brighter spot, so the red ✕ was not counted.

## hotpix_delta
title: hot-pixel delta = {hotpix_delta}
shown: the camera image before the hot-pixel fix
legend: red box = a hot pixel, replaced by the median of its 3 × 3 neighbourhood

The hot-pixel delta is how far above the median of its 3 × 3 neighbourhood a
pixel must be to count as hot and be replaced by that median. On a camera
with more than 8 bits the hot-pixel delta is scaled with the brightest
pixel, so it stays on the 0-255 scale. A hot-pixel delta of 0 turns the
correction off.

Replaced on this frame: {n_hot}. In the event window: {hot_ev}; in the
background window: {hot_bg}.

**In the windows**, a red box marks each pixel that was replaced as hot.
Lower the hot-pixel delta and more red boxes appear; raise the hot-pixel
delta and fewer pixels count as hot.

## bg_blur_size
title: background kernel = {kernel} px
shown: the background estimate itself, on the same levels as the camera image
legend: amber dashed box = the size of the background kernel, {kernel} × {kernel} px

The background is a Gaussian blur of the frame, made in two passes:

1. a plain blur of size {kernel} px;
2. the same blur again with every pixel above {mask_nsigma} σ left out, so
   the spots do not raise their own baseline.

The background-subtracted image is the frame minus this estimate, clipped at
zero. It is what every cut and feature is measured on.

A larger kernel follows uneven illumination more loosely. A kernel close to
the size of a spot follows the spot itself and eats its light. Background
under the event: {bg_ev}; in the background window: {bg_bg}.

**In the windows**, the image is the background estimate, not the camera
image; it is smooth because it is a blur. The amber dashed box shows the
size of the background kernel: the background at each pixel is a weighted
mean over roughly that square.

## adaptive
title: adaptive threshold: {adaptive}
shown: the background-subtracted image
legend: amber fill = a pixel above the threshold used ({thresh})
legend: white box = the event's peak pixel

- With adaptive thresholding **on**, the threshold used is the larger of the
  peak threshold and noise multiple × σ.
- With adaptive thresholding **off**, the threshold used is the peak
  threshold alone, and the noise multiple is not used.

{thresh_rule}

**In the windows**, every pixel above the threshold used is coloured amber,
and a white box marks the event's peak pixel. Switch adaptive thresholding
on and off to see the amber area change when noise multiple × σ is higher
than the peak threshold.

## spot_max_radius
title: max aperture = {spot_max_radius} px
shown: the background-subtracted image
legend: amber dashed circle = the max aperture
legend: white circle = the aperture the event grew to

Each spot's light is summed over a circular **aperture**. It starts at 1 px
and grows ring by ring; it stops when a ring adds less than {plateau_pct} %
of the light already inside, or when it reaches the max aperture.

This event grew to {ev_r} px ({stop_reason}): {ev_area} pixels holding a
luminosity of {ev_lum}.

The max aperture changes what is measured, never the count.

**In the event window**, the dashed amber circle is the max aperture, the
largest the aperture may grow, and the solid white circle is the aperture
the event actually grew to. The two circles coincide when the event reached
the max aperture.

## isolation_factor
title: isolation factor = {isolation_factor}
shown: the camera image
legend: white circle = the event's aperture
legend: white dashed circle = the isolation circle (amber when the event is crowded)
legend: red ring = a neighbouring spot
legend: red dashed line = the way to the nearest neighbour

A spot is isolated when its nearest neighbour is further away than
isolation factor × its aperture radius.

This event's isolation circle: {isolation_factor} × {ev_r} px = {iso_r} px; nearest neighbour
{ev_nn} → this event is **{ev_iso}**. On this frame {n_iso} of {n} spots are isolated.

The isolation factor changes which spots are trusted for shape, never the count.

**In the event window**, the solid white circle is the event's aperture
and the dashed circle is the isolation circle; the dashed circle is white
when the event is isolated and amber when it is crowded. A red ring marks a
neighbouring spot and the red dotted line points to the nearest neighbour.
The event is isolated when the nearest neighbour lies outside the dashed
circle.

## names
title: the names you can use in braces
shown: the camera image

This topic is never shown by the program; it is the list of names.

- the settings: {abs_thresh} {n_sigma} {sum_thresh} {spread_min} {min_dist}
  {hotpix_delta} {kernel} {adaptive} {spot_max_radius} {isolation_factor}
  {aperture_radius} {mask_nsigma} {plateau_pct} {nms}
- the frame: {n} {sigma} {thresh} {nsig} {mask_level} {n_hot} {n_iso}
  {lum_count} {bg_res} {n_suppressed}
- sentences written by the program: {thresh_rule} {abs_note}
- the two windows: {hot_ev} {hot_bg} {masked_ev} {masked_bg} {bg_ev} {bg_bg}
  {above_bg}
- the event: {ev_peak} {ev_sum5} {ev_spread} {ev_lum} {ev_r} {ev_area}
  {ev_nn} {ev_iso} {iso_r} {stop_reason}
- the event against each cut, the verb "passes" or "fails": {pass_peak}
  {pass_abs} {pass_sum} {pass_spread}
