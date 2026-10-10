# learn — the spot features, defined once

Every lesson that talks about a feature (spots, histogram, pca) takes its
definition from here: a lesson text writes {about} where the definition goes.

- One `## key` section per feature; the key is the name the program uses.
- `title:` is the feature's name; `shown:` is its meaning in one line (the
  histogram and pca lessons quote it).
- The body is the definition, in Markdown. Live numbers are not available
  here: write them in the lesson's own text.
- Everything above the first `## ` is never shown.

## luminosity
title: luminosity
shown: the light of the spot: the sum of the pixels inside its aperture

The **luminosity** is the light inside the spot's aperture, on the
background-subtracted image, with the residual background removed:

> luminosity = sum of the aperture pixels − residual background × number of
> aperture pixels

The residual background is the mean of the spot-free pixels of the frame;
it removes the small positive floor that the clipping at zero leaves.

The luminosity depends on the brightness of the spot: a brighter particle
gives a larger luminosity. It is the natural measure of how much light one
particle makes.

## radius_used
title: aperture radius
shown: the radius the spot's aperture grew to, in pixels

The **aperture** is the circle, centred on the peak pixel, inside which the
spot's light is summed. Its radius is not fixed: it starts at 1 px and grows
ring by ring, and stops when a ring adds less than a set fraction of the
light already inside (the plateau), or when the radius reaches the max
aperture.

A wide spot grows a large aperture; a sharp spot stops early. The aperture
radius is the size every other feature of the spot is measured in.

## area
title: aperture area
shown: the number of pixels inside the aperture

The **aperture area** is the number of pixels whose centre lies inside the
aperture: about π × radius², fewer at the edge of the frame.

## peak
title: peak
shown: the brightest pixel of the spot, background subtracted, 0-255 scale

The **peak** is the value of the spot's brightest pixel in the
background-subtracted image, on the 0-255 scale. Detection requires it to
be above the threshold used.

The peak depends on the brightness of the spot, and also on how sharp the
spot is: the same light concentrated on fewer pixels gives a higher peak.

## sum5x5
title: 5x5 sum
shown: the light of the 5 × 5 pixels centred on the peak

The **5x5 sum** is the sum of the 25 pixels of the 5 × 5 box centred on the
peak pixel, on the background-subtracted image. Detection requires it to be
above the 5x5 sum min.

Unlike the luminosity, the 5x5 sum uses a fixed box, the same for every
spot.

## radial_sigma
title: radial σ
shown: the size of the spot: the light-weighted RMS (root mean square) distance from its centroid

The **radial σ** measures the size of the spot. Each pixel of the aperture
is weighted by its light w; the **centroid** is the light-weighted mean
position, and

> radial σ = √( Σ w r² / Σ w )

with r the distance of a pixel from the centroid. For a round Gaussian spot
of width σ, the radial σ is √2 σ.

The radial σ does not depend on the brightness: doubling every pixel leaves
it the same.

## concentration
title: concentration
shown: the fraction of the spot's light within 2 px of its centroid

The **concentration** is the fraction of the aperture's light that lies
within 2 px of the centroid:

> concentration = Σ w (r ≤ 2 px) / Σ w

A sharp spot keeps most of its light in the core and has a concentration
close to 1; a wide or flat spot has a small concentration.

The concentration does not depend on the brightness.

## eccentricity
title: eccentricity
shown: how elongated the spot is: 0 for a round spot, close to 1 for a line

The **eccentricity** measures how elongated the spot is. The light-weighted
covariance of the aperture pixels' positions gives the spread of the light
along its long axis, the variance λ₁, and along its short axis, the
variance λ₂, and

> eccentricity = √(1 − λ₂ / λ₁)

A round spot has eccentricity 0; a spot stretched along one direction, for
example by two particles side by side or by a moving particle, has an
eccentricity close to 1.

The eccentricity does not depend on the brightness.

## profile_slope
title: profile slope
shown: how fast the spot's light falls off with distance from its centroid

The **profile slope** describes how fast the light falls off away from the
centroid. The logarithm of each aperture pixel's light is plotted against
its distance from the centroid, and a straight line is fitted:

> log w ≈ slope × r + constant

A sharp spot falls off fast and has a steep, strongly negative slope; a wide
spot has a slope close to 0. With fewer than 3 pixels holding light, the
slope is set to 0.

The profile slope does not depend on the brightness.

## nn_dist
title: nearest-neighbour distance
shown: the distance from the spot to the nearest other spot of the same image

The **nearest-neighbour distance** is the distance, in pixels, from the
spot's peak pixel to the peak pixel of the nearest other spot of the same
image; ∞ when the spot is alone in the image.

## is_isolated
title: isolated
shown: whether the nearest spot is far enough for the aperture's light to be the spot's own

A spot is **isolated** when its nearest neighbour is further away than
isolation factor × its aperture radius. Only then does all the light in its
aperture belong to it alone. A crowded spot shares light with its neighbour,
so its luminosity and shape are not those of one particle; the histogram and
pca pages use isolated spots only, by default.
