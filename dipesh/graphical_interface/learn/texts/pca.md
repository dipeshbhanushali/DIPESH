# learn / pca — the lesson texts

Edit freely while the program runs: every time this file is saved, the text
on screen is read again.

The format is the one of image.md: `## key`, then `title:`, `shown:`,
`legend:` lines, then the explanation in Markdown with live values in braces.
{about} is replaced by the definition of the feature under the mouse, from
features.md.

The keys are the controls of the pca page (feature for any feature check
box, logf, iso, ell, axes, stats), its two groups (features, options), the
two plots (scatter, loadings) and the introduction (intro).

Live values: {n} {n_features} {datasets} {logf} {iso} {ell} {axes} {pi}
{pj} {ev_i} {ev_j} {ev_1} {ev_12} {pc1_mostly} {pc1_sep} {pair}; for a
feature: {feature} {feature_meaning} {checked} {logged} {load_i} {load_j}

## intro
title: pca — every feature at once
legend: a point in a dataset's colour = one spot

The histogram looks at one feature at a time. **PCA** (principal component
analysis) looks at all the chosen features at once, and finds the
directions in which the spots differ most.

Each spot is a point with one coordinate per feature. PCA turns these
coordinates into new ones, the **principal components** PC1, PC2, …: PC1
is the direction along which the spots spread the most, PC2 the next one at
right angles to PC1, and so on. The scatter plot shows every spot on two of
them; the bar plot below shows how much each feature contributes to them
(the **loadings**).

Rest the mouse on any control on the right, or on a plot: the plots show
what it does and this text explains it. PCA needs **Run all**.

On show: {n} spots ({datasets}), {n_features} features; {pi} and {pj} hold
{ev_i} and {ev_j} of the variance.

## features
title: features
legend: a point in a dataset's colour = one spot

The check boxes choose **which features enter the PCA**. At least two are
needed. Rest on one of them to see its definition and its place in the
plots.

## options
title: options
legend: a point in a dataset's colour = one spot

These controls choose how the features are prepared, which spots enter,
what is drawn, and which two components are plotted.

## feature
title: {feature}: {checked}
legend: amber line = the direction in which {feature} grows, in the scatter
legend: amber box = the feature's two loading bars

{about}

In the PCA this feature is **{checked}**, and it {logged} taken as log₁₀
first.

Its loadings: {load_i} on {pi}, {load_j} on {pj}. A loading is the weight
of the feature in a component, between −1 and +1: a large positive loading
means that spots with more of this feature sit further to the positive side
of that component.

**In the scatter**, the amber arrow points the way this feature grows:
spots further along the arrow have more of it. **In the loadings**, the
amber boxes mark the feature's two bars. Nothing is drawn when the feature
is not included.

## logf
title: log brightness: {logf}
legend: a point in a dataset's colour = one spot

- With **log brightness** switched on, luminosity, peak and 5x5 sum enter
  the PCA as log₁₀ of their value. They span decades; taking the logarithm
  lets PCA see the shape of their distribution rather than their few
  largest values.
- With it switched off, they enter as they are.

It is switched **{logf}** now.

Before the PCA, every feature is **standardised**: its mean is subtracted
and it is divided by its standard deviation, so every feature counts the
same whatever its unit.

## iso
title: isolated spots only: {iso}
legend: a point in a dataset's colour = one spot

- With **isolated spots only** switched on, only isolated spots enter: the
  light of their aperture is their own.
- With it switched off, crowded spots enter too, with shapes mixed with
  their neighbours' light.

It is switched **{iso}** now. Spots with a value that cannot be used (for
example a log of 0) are always left out.

## ell
title: 2σ ellipses: {ell}
legend: plus in a dataset's colour = the mean of that dataset

The ellipse of a dataset is the outline that holds most of its points: it
is drawn from the covariance of the dataset's points in the two plotted
components, at two standard deviations along each of its axes. Two
datasets whose ellipses do not overlap are told apart by these two
components.

- With **2σ ellipses** switched on, each dataset's ellipse is drawn,
  filled faintly in its colour.
- With it switched off, only the points are drawn.

**In the scatter**, the large plus in each dataset's colour is the mean of
its points, the centre of its ellipse.

## axes
title: axes: {axes}
legend: amber line = the direction in which a feature grows
legend: white dashed line = the zero of each component

The scatter plots the spots on two principal components; this control
chooses which two. {pi} holds {ev_i} of the variance of the spots, {pj}
{ev_j}. Together PC1 and PC2 hold {ev_12}.

Every component is centred: the mean spot sits at 0, 0.

**In the scatter**, the dotted white lines are the zero of each
component, and each amber arrow points the way one feature grows (a
**biplot**): features whose arrows point the same way grow together; an
arrow along the horizontal axis is a feature that {pi} is made of.

## stats
title: what the numbers on the right say
legend: plus in a dataset's colour = the mean of that dataset
legend: dashed line in a dataset's colour = the mean of that dataset along PC1

The numbers on the right of the page summarise the PCA:

- **variance explained**: the share of the spots' total spread each
  component holds; here PC1 {ev_1}.
- **PC1 separation** (with exactly two datasets, {pair}): the separation
  score of the two datasets along PC1, |mean₁ − mean₂| / (σ₁ + σ₂) = {pc1_sep};
  above about 1.5 they separate cleanly.
- **PC1 is mostly**: the three features with the largest loadings on PC1,
  with their sign: {pc1_mostly}. Spots with a large PC1 have more of the
  features with + and less of those with −.

**In the scatter**, the large plus marks each dataset's mean; when PC1 is
the horizontal axis, the dashed vertical lines show the two means along
PC1, whose gap the separation score measures.

## scatter
title: the scatter plot
legend: a point in a dataset's colour = one spot
legend: amber line = the direction in which a feature grows

Each point is one spot, placed by its {pi} and {pj}; each dataset has its
colour and marker, named in the legend of the plot. The axis labels give
each component's share of the variance.

**In the scatter**, the amber arrows show the way each feature grows, as
for the **axes** control: they tell what moving along the plot means.

## loadings
title: the loadings
legend: amber box = a bar of the three largest loadings on {pi}

Each feature has two bars: light for {pi}, dark for {pj}. The height of a
bar is the feature's loading on that component, between −1 and +1: how
much, and in which direction, the component follows that feature.

**In the loadings**, the amber boxes mark the three features with the
largest loadings on {pi}: those {pi} is mostly made of.
