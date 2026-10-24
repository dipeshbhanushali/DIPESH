# learn / histogram — the lesson texts

Edit freely while the program runs: every time this file is saved, the text
on screen is read again.

The format is the one of image.md: `## key`, then `title:`, `shown:`,
`legend:` lines, then the explanation in Markdown with live values in braces.
{about} is replaced by the definition of the feature on show, from
features.md.

The keys are the controls of the histogram page (feature, logx, bins, iso,
norm, a, b, cut, stats), its two groups (what, compare), the plot (plot)
and the introduction (intro).

Live values: {feature} {feature_meaning} {log} {unit} {bins} {bin_width}
{lo_edge} {hi_edge} {iso} {norm} {n_datasets} {datasets} {a} {b} {lo} {hi}
{n_lo} {n_hi} {mean_lo} {mean_hi} {sd_lo} {sd_hi} {dmean} {sdsum} {sep}
{verdict} {cut} {cut_shown} {lo_above} {hi_below}

## intro
title: histogram — one feature, every dataset
legend: a filled outline in a dataset's colour = the histogram of that dataset

The histogram page compares one spot feature across the datasets: how
often each value occurs among the spots of each dataset. If two datasets
are different kinds of particles, a feature that tells them apart shows two
histograms side by side; a feature that does not, shows them on top of each
other.

On the right, the page measures how well the feature separates two chosen
datasets (the **separation score**) and where to cut between them (the
**best cut**). The table above shows the numbers behind both: its first column is the lower dataset, its second the higher one.

Rest the mouse on any control on the right, or on the plot: the plot shows
what it does and this text explains it. The histogram needs **Run all**: it
uses every counted spot of every dataset.

On show: {feature}, for {datasets}.

## what
title: what to plot
legend: a filled outline in a dataset's colour = the histogram of that dataset

These controls choose **what the histogram counts**: which feature, on
which scale, in how many bins, from which spots, and whether the datasets
are scaled to the same total.

## compare
title: compare two
legend: a filled outline in a dataset's colour = the histogram of that dataset

These controls choose **which two datasets are compared**, and whether the
best cut between them is drawn. The separation score and the best cut below
them are computed for these two.

## feature
title: feature: {feature}
legend: a filled outline in a dataset's colour = the histogram of that dataset

The feature is the spot measurement the histogram counts. Every spot of
every dataset adds one count to the bin its value falls in.

{about}

## logx
title: log scale: {log}
legend: a filled outline in a dataset's colour = the histogram of that dataset

- With **log scale** switched on, the histogram counts log₁₀ of the
  feature, and spots with a value of 0 or less are left out. The bins are
  then equal steps in ratio: one bin may span 100 to 200, the next 200 to
  400.
- With **log scale** switched off, the histogram counts the feature itself,
  in equal steps.

Brightness features (luminosity, peak, 5x5 sum) span decades, so they are
plotted on a log scale by default; choosing such a feature switches the log
scale on. A feature whose values are all 0 or less, such as the
profile slope (always negative), has nothing left on a log scale: the plot
is then empty; switch the log scale off to see it. The mean, σ, separation score and cut in the table are computed
on what is plotted: on log₁₀ of the feature when the log scale is on.

Log scale is now **{log}**.

## bins
title: bins = {bins}
legend: white dashed line = a bin edge

The range from the smallest to the largest value of every dataset is cut
into {bins} equal bins, each {bin_width} wide ({unit}{feature}, from
{lo_edge} to {hi_edge}). Every dataset is counted in the same bins, so
their histograms can be compared bar by bar.

More bins show more detail but fewer spots per bin, so a noisier histogram;
fewer bins give a smoother but coarser shape.

**In the plot**, the dotted lines are the bin edges.

## iso
title: isolated spots only: {iso}
legend: a filled outline in a dataset's colour = the histogram of that dataset

- With **isolated spots only** switched on, only isolated spots are
  counted: their light belongs to one particle.
- With it switched off, every spot is counted, crowded ones too; a crowded
  spot shares light with its neighbour, so its luminosity is not one
  particle's.

It is switched **{iso}** now. In the table, n is the number of spots
counted for each of the two compared datasets.

## norm
title: normalise each dataset: {norm}
legend: a filled outline in a dataset's colour = the histogram of that dataset

- With **normalise each dataset** switched on, each histogram is divided by
  the number of its spots, so it shows the fraction of the dataset's spots
  in each bin, and every histogram adds up to 1. Datasets of different
  sizes can then be compared by their shape.
- With it switched off, the histogram shows the number of spots in each
  bin, and a large dataset towers over a small one.

It is switched **{norm}** now. The separation score and the best cut do not
change with it: they use the spots, not the bars.

## a
title: lower dataset: {a}
legend: dashed line in a dataset's colour = the mean of that dataset
legend: band in a dataset's colour = mean ± σ of that dataset

The two datasets to compare. The page expects the **lower dataset** to
have the smaller values; if it has the larger ones, the two are swapped for
the cut, and the table names them by where they actually lie.

Now: lower {lo}, mean {mean_lo}, σ {sd_lo}, n = {n_lo}; higher {hi}, mean
{mean_hi}, σ {sd_hi}, n = {n_hi}.

**In the plot**, a dashed line in each dataset's colour marks its mean, and
a faint band of the same colour spans mean − σ to mean + σ.

## b
title: higher dataset: {b}
legend: dashed line in a dataset's colour = the mean of that dataset
legend: band in a dataset's colour = mean ± σ of that dataset

The second dataset of the comparison, expected to have the larger values.

Now: lower {lo}, mean {mean_lo}, σ {sd_lo}, n = {n_lo}; higher {hi}, mean
{mean_hi}, σ {sd_hi}, n = {n_hi}.

**In the plot**, a dashed line in each dataset's colour marks its mean, and
a faint band of the same colour spans mean − σ to mean + σ.

## stats
title: separation score = {sep}
legend: dashed line in a dataset's colour = the mean of that dataset
legend: band in a dataset's colour = mean ± σ of that dataset

The separation score measures how far apart the two histograms are,
compared with how wide they are:

> separation score = |mean₁ − mean₂| / (σ₁ + σ₂)

Here: |{mean_hi} − {mean_lo}| / ({sd_lo} + {sd_hi}) = {dmean} / {sdsum} =
**{sep}**, so {feature} {verdict}.

- above about 1.5 the two datasets separate cleanly: their bands do not
  touch;
- below about 0.5 they overlap heavily.

**In the plot**, the dashed lines are the two means and the bands their
mean ± σ: the score compares the gap between the lines with the widths of
the bands.

## cut
title: best cut = {cut_shown}
legend: a strongly filled bar in the lower dataset's colour = its spots above the cut, taken for the higher dataset
legend: a strongly filled bar in the higher dataset's colour = its spots below the cut, taken for the lower dataset

The best cut is the value of {feature} that best splits the two datasets:
spots below it are called lower, spots above it higher. It is the value, of
400 tried between the smallest and the largest, at which the mean of the
two mistakes is smallest:

> mistakes = (lower spots above the cut + higher spots below the cut) / 2,
> each as a fraction of its dataset

Here: {lo_above} of {lo} lie above the cut, and {hi_below} of {hi} lie
below it.

- With **draw best cut** switched on, the page draws the cut as a dashed
  amber line.
- With it switched off, the cut is still computed and listed, not drawn.

**In the plot**, the strongly filled bars are the mistakes: in the lower
dataset's colour, its spots above the cut; in the higher dataset's colour,
its spots below the cut.

## plot
title: the histogram
legend: a filled outline in a dataset's colour = the histogram of that dataset

Each dataset is one filled outline in its colour; its name and number of
spots are in the legend of the plot. The horizontal axis is
{unit}{feature}; the vertical axis is the number of spots in each bin, or
the fraction of the dataset's spots when **normalise each dataset** is on.
