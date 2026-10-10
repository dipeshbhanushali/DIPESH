# learn / overview — the lesson texts

Edit freely while the program runs: every time this file is saved, the text
on screen is read again.

The format is the one of image.md: `## key`, then `title:`, then the
explanation in Markdown. There are no figures here, so no `shown:` or
`legend:` lines, and no live values.

The keys are: intro, program, session, image, spots, histogram, pca, plots,
pickup, learn, wf_count, wf_separate, wf_tune, wf_pickup. The list on the
left of the screen is in the program (overview_lesson.py); only the texts
are here.

## intro
title: overview — what the pages are for

**DIPESH** stands for **Detection and Imaging of Pbar Events, Spots and
Hits**; "pbar" is the physicists' short name for the antiproton, written p̄.
DIPESH counts antiprotons in camera images of the detector screen, measures
each spot of light, and compares runs. The top bar is one page per step:
**image**, **spots**, **histogram**, **pca** (principal component
analysis), **plots**, **pickup**, and this **learn** page.

Rest the mouse on a name in the list on the left to read what that page is
for and how to use it. Click a name to keep its text while you move the
mouse. The **workflows** at the bottom of the list describe common tasks,
page by page.

The other learn tabs (image, spots, histogram, pca) explain each page in
depth, on your own data: what every number means and what every setting
does.

## program
title: what DIPESH does

**DIPESH** is short for **Detection and Imaging of Pbar Events, Spots and
Hits**: pbar (p̄) is the antiproton, and the events, spots and hits are the
flashes of light the antiprotons make on the detector.

When antiprotons hit the detector, each one makes a small spot of light on
the screen, and the camera takes a picture. DIPESH:

1. **finds the spots** in each picture, and counts them: that count is the
   number of antiprotons in the run;
2. **measures each spot**: how bright it is, how big, what shape, and
   whether it stands alone;
3. **compares runs and datasets**: a scan of a trap setting, antiproton
   runs against background runs, and so on;
4. **reads the pickup signals** of the oscilloscopes recorded with each
   run, and measures the pulse they show.

The left column of the window is the list of runs you added, in
**datasets**: one dataset per folder, each with its own colour. The big
number on the right is the antiproton count of the run you selected. The
console at the bottom reports what the program did.

## session
title: a session, step by step

1. **Add data**: *Add folder…* (Ctrl+O), or drop a folder on the list. A
   folder of runs becomes one dataset. Add background runs or ion runs as
   their own datasets, so the pages can compare them.
2. **Look at a run**: click it in the list. The **image** page shows the
   picture with every counted spot circled, and the count.
3. **Check the detection**: step through a few runs (PgUp / PgDn). If spots
   are missed or noise is counted, adjust the settings on the right; the
   count follows as you drag.
4. **Run all** (Ctrl+R): counts every run of every dataset with the
   settings you chose. The list fills with counts.
5. **Compare**: **plots** shows the count against a run parameter;
   **histogram** and **pca** show whether two datasets contain different
   kinds of spots; **pickup** shows the oscilloscope pulses.
6. **Export** (Ctrl+E): writes the counts, the spots and the settings to
   files, and marked images if you want them.

If you change a setting after Run all, the button turns amber and reads
*Run all again*: the counts in the list are then out of date.

## image
title: image

The **image** page shows the picture of the run you selected, with every
counted spot circled. The circle is the area the spot's light was summed
over: white for a spot standing alone, amber for a spot close to another.

Use it to:

- **see what was counted**, run by run, and spot what was missed or
  counted by mistake;
- **tune the detection** with the settings on the right; the picture and
  the count follow as you drag;
- **read the run parameters** of the run, listed under the picture;
- **check the camera**: switch the display to *background subtracted* to
  see what the detector really looks at.

The settings on the right are the same on the **image** and **spots**
pages. *Save…* writes them to a file and *Load…* reads them back, so a
result can always be reproduced.

## spots
title: spots

The **spots** page lists every counted spot of the run as a table: where it
is, how bright, how big, what shape, and whether it stands alone. Click a
column header to sort by it; double-click a row to see that spot on the
image page.

Use it to:

- **find the odd ones**: sort by brightness or size and look at the largest
  or smallest spots, which are often two particles together or a flicker;
- **see a whole dataset** at once, after Run all, with *spots from: whole
  dataset*;
- **save the table** as a CSV file (comma-separated values, which any
  spreadsheet opens) for your own analysis.

## histogram
title: histogram

The **histogram** page takes one measurement, for example the brightness,
and shows how it is spread among the spots of each dataset: one curve per
dataset. It needs Run all first.

Use it to:

- **compare datasets**: if antiproton spots and background spots have
  different brightness, their curves sit apart; if they look the same, the
  curves overlap;
- **find a cut**: for two chosen datasets the page gives a *separation
  score* (how far apart the curves are) and the *best cut*, the value that
  best splits them, with the share of spots on the wrong side;
- **try each measurement in turn** to find the one that separates best.

## pca
title: pca — principal component analysis

**pca** stands for **principal component analysis**, a standard method of
statistics for looking at many measurements at once. The "components" are
new axes, built from the measurements, along which the data spread the
most; the "principal" ones are the few that matter.

The **pca** page uses it to look at all the measurements of a spot at once
instead of one at a time. It needs Run all first.

Each spot becomes a point on a plot; spots that are alike sit close
together, and each dataset is drawn in its own colour with an ellipse around
its points. The bar plot below says which measurements matter most for the
spread of the points.

Use it to:

- **see whether datasets form separate groups**: separate ellipses mean the
  spots differ in kind;
- **learn which measurements make the difference**: the tallest bars;
- **check for mixed datasets**: points of one colour inside another
  colour's ellipse are spots that look like the other kind.

## plots
title: plots

The **plots** page draws any quantity of a run (the count, the light, a
pickup number) against any run parameter, one point per run, with repeated
runs averaged and an optional fit. It needs Run all first.

Use it to:

- **see a scan**: the count against the trap setting that was scanned, for
  example;
- **compare datasets** on the same axes;
- **fit a trend**: a line, a parabola or an exponential through the
  points;
- **save the points** behind the plot as a CSV file (comma-separated
  values, which any spreadsheet opens).

## pickup
title: pickup

The **pickup** page shows the oscilloscope traces recorded with the run:
the signal the particles induce on the pickup electrodes as they pass. Both
scopes are drawn on one time axis; the trap's radio frequency, which
swamps the signal, is filtered out.

Use it to:

- **see the pulse** of a run, and read its time, height, area and width in
  the table below;
- **check the timing** between the two scopes;
- **spot a run without a signal**, or with a noisy trace.

The pickup numbers of every run go into the export and can be plotted on
the **plots** page.

## learn
title: learn

The **learn** page is this one: one tab per page of the program, each
explaining that page on your own data. Rest the mouse on a setting or a
number, and the figures show what it does and the text explains it with the
numbers of the run you selected.

The settings on the learn tabs are copies: you can try anything without
changing the analysis. Press **Apply** to hand them to the program.

## wf_count
title: workflow: count the antiprotons of a scan

1. **Add the runs** of the scan as one dataset (*Add folder…*).
2. **Look at a few runs** on the **image** page: are the spots circled, and
   nothing else? If not, adjust the settings on the right until the
   circles sit on the spots in a bright run and in a faint run.
3. **Run all**.
4. On the **plots** page, choose the parameter that was scanned on the
   horizontal axis and *count* on the vertical axis. Repeated runs are
   averaged; add a fit if you want one.
5. **Export** the counts, with the settings, so the result can be
   reproduced.

## wf_separate
title: workflow: tell antiprotons from background

1. **Add two datasets**: the antiproton runs and the background runs (or
   the ion runs), from their own folders.
2. **Run all**, with settings that count the spots of both.
3. On the **histogram** page, choose a measurement and the two datasets:
   the *separation score* says how different the spots are, and the *best
   cut* where to split them. Try the brightness first, then the shape
   measurements.
4. On the **pca** page, see whether the two datasets form separate groups
   when all measurements are taken together, and which measurements make
   the difference.
5. If a measurement separates them, use the cut on the **spots** page
   (sort by that column) to see which spots are which.

## wf_tune
title: workflow: tune and check the detection

1. Select a typical run and open **learn / image**. Rest the mouse on each
   setting on the right to see what it does, on your run.
2. Move the settings on the learn tab: the count, the windows and the table
   follow, and the analysis is untouched. The *threshold* decides how faint
   a spot may be; the *min separation* decides when two spots close
   together count as one.
3. Check the result on a faint run and on a crowded run as well.
4. Press **Apply**: the settings go to the **image** page and to Run all.
5. **Save…** the settings to a file, so they can be loaded again later.

## wf_pickup
title: workflow: check the pickup signals

1. Select a run and open the **pickup** page. If the traces do not appear,
   press *Find in files* so the program reads the scope names from the
   files of the run.
2. Keep *remove trap RF* on (RF is the trap's radio frequency): without it
   the radio frequency hides the
   pulse.
3. Read the pulse's time, height, area and width in the table below the
   traces, and compare the two scopes.
4. After **Run all**, open the **plots** page and plot a pickup number, for
   example the pulse area, against the count or against a run parameter.
