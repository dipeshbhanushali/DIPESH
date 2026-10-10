# How to build a learn pane — workflow (draft)

The steps we followed for learn / image, written so the next panes (spots,
histogram, pca) can be built the same way. Preliminary: to be refined as we
build the next one.

## 1. Ground rules

- Work only inside `DIPESH/dipesh/learn/`. Anything outside (other source
  files, tests, packaging) needs the authors' permission first.
- Reuse the program's own pieces (pages, panels, analysis functions); never
  write a second version of the analysis.
- After a code change the program must be restarted; after a text change
  (`texts/*.md`) it must not.

## 2. Study the main page the pane explains

- Read the page's code, its settings panel, and the analysis functions it
  calls, down to the formulas.
- List every number and setting the user can see on that page: these
  become the topics of the pane.

## 3. Lay out the pane

- A tab in the learn bar, under the "learn" tab of the top bar.
- Keep the controls where the original page has them; the rest of the area
  holds the explanations.
- Always a **description** section for the text (step 7).
- When meaningful, **figures** with legends, and **tables** of values.
- If the page has settings, learn uses its own copy with the **Apply**
  button and the warning "Press to apply settings for the analysis"
  (step 5).

Example, learn / image: the detection panel stays on the right, as on the
image page; on the left, two figures ("event" and "background") with a
legend; in the middle, a table of the event's values above the
description.

## 4. Compute from the real pipeline

- Call the same functions as the analysis, keeping the intermediate results
  (for image: camera image, hot pixels, background, background-subtracted
  image, candidates).
- Check numerically that they equal what the analysis produces, on the test
  data.
- Choose the example shown: the cleanest first (for image: the most
  isolated spot), with ◀ ▶ to step through the others.

## 5. Keep learn's settings apart (when the page has settings)

- learn has its own session and live detection; its sliders change only
  the pane.
- **Apply** hands the settings to the main page, exactly as if its own
  sliders had been moved.
- Settings changed on the main page reach learn, unless learn has changes
  not yet applied.

## 6. Define each topic

Hovering with the mouse is the way to select an explanation: resting the
mouse on a control or a number selects its topic, and the description,
figures and tables change to explain it. Leaving the controls returns to the
introduction.

So every control and number of the page is a topic, and for each one decide:

- what the description says (step 7);
- when there are figures: which image they show, which marks are drawn
  (colour + shape), and how big the view must be for the marks to fit;
- when there is a table: which rows are highlighted;
- which live values the text needs.

## 7. Write the texts in `texts/<pane>.md`

- One `## key` section per topic, with `title:`, `shown:`, `legend:` lines
  and the explanation in Markdown; `{name}` for live values.
- Writing rules:
  - give every sentence its subject; write the noun, not only the adjective
    ("adaptive thresholding is on", not "adaptive is on");
  - name the setting instead of "it" or "this";
  - explain every acronym the first time it appears in a lesson (DIPESH,
    PCA, MCP, RF, CSV, RMS, …): the reader may not know it;
  - for an option, describe every case (on and off), then say which one
    applies now;
  - say what is computed, then why, then what this frame gives;
  - end with a paragraph **In the windows** saying what each mark means;
    the legend repeats the marks in short.
- Fixed wording belongs in the `.md` file, so the authors can edit it; the
  code only provides numbers and states.
- The text is read again whenever the file is saved: edit it while the
  program runs.

## 8. Test

- Offscreen, with the synthetic test data (`tests/helpers/make_testdata.py`):
  every topic renders, no value is missing, the marks match the legend
  (screenshots).
- Hover, ◀ ▶, Apply, and live reload of the text file.
- The full test suite: no new failures.

## 9. Review with the authors

- The authors read the pane on real data and correct the texts directly in
  the `.md` file.
- Comments that need code changes go to `review/`; the day's work to
  `summary/`; the next steps to `plan/`.
