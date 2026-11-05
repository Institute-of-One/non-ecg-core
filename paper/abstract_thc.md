# IORN-011 -- title, abstract and keywords for Technology and Health Care

Format read off the journal's own submission guidelines on 2026-11-05: a
**structured** abstract of **200 words**, stating the purpose, the major
findings and the conclusions; **4 to 7** keywords; Sage Vancouver references;
the declarations in the article under `Statements and Declarations`; review
**single-anonymized**. The journal states no word limit for an Original
Research Article and lists no short article type, so nothing here is written
to fit a shorter receptacle.

The headings are the ones the journal's own accepted papers print
(`10.3233/thc-248006`), not a guess from the prose of the guidelines.

**Every number is a marker.** `paper/build_submission_thc.py` resolves them
from `paper/frozen/manifest.json`, and the word count is taken after they are
resolved, so the limit is measured on what the editor will read.

## Title

Cardiac period estimation from non-gated helical CT: sampling criteria and exploratory evaluation

## Abstract

**BACKGROUND:** Cardiac motion undulates the mediastinal border in a non-gated helical chest CT; a recoverable period would let an existing scan be sorted by phase.

**OBJECTIVE:** To state the sampling conditions that make the period recoverable, test them against real acquisitions, and measure how far an image-based estimate can be trusted.

**METHODS:** The cycles needed were measured over [[results:manifest.json:metrics.sensitivity_cells]] simulated conditions, evaluated against [[results:manifest.json:metrics.header_series]] real series through their headers alone, and tested on [[results:manifest.json:metrics.cohort_analysed]] image series under a criterion frozen in advance.

**RESULTS:** Cycles written and samples per cycle multiply to L/dz, so speed only divides a fixed budget. The threshold is [[results:manifest.json:metrics.n_min_fundamental]] written cycles, [[results:manifest.json:metrics.n_min_matched]] for a matched estimator — empirical, not universal. At an assumed cardiac extent, [[results:manifest.json:metrics.records_below_100bpm_border_percent]] per cent of real series meet the requirements below [[results:manifest.json:metrics.prediction_ceiling_bpm]] bpm. On images, [[results:manifest.json:metrics.cohort_recovered]] of [[results:manifest.json:metrics.cohort_analysed]] met the self-consistency criterion, yet their cost minima are no deeper than the rejections' and their levels prefer rates differing by [[results:manifest.json:metrics.flatness_level_spread_accepted_min]] to [[results:manifest.json:metrics.flatness_level_spread_accepted_max]] bpm.

**CONCLUSIONS:** The requirements are computable from headers before any image is analysed. Self-consistency alone does not establish that a period was found: a fit needs the depth of its minimum and a check on what it fitted.

## Keywords

Computed tomography; Cardiac imaging techniques; Image processing,
computer-assisted; Signal processing, computer-assisted; Sampling studies;
Reproducibility of results

## Notes for the author

- **200 words is the limit and the build enforces it after resolving the
  markers.** The PMB abstract was 295 words under a 300-word limit with four
  headings of its own (Objective / Approach / Main results / Significance);
  this is the same content under this journal's five.
- What was dropped to reach 200, from a first draft of 252 words: the sentence
  announcing the auxiliary simulation, which has moved to the supplementary
  material; the sentence deriving the time axis from the constant table speed,
  which the Results still carry as the budget identity and the Theory derives
  in full; the note that phase and ejection fraction were not examined, which
  the Introduction and the Discussion both state; and the qualifying clause
  that the per-cent figure is a statement about conditions rather than
  outcomes, which the Results and the Discussion make in full and which the
  abstract no longer needs, because it no longer says anything about outcomes.
  No result was dropped.
- Six keywords, within the journal's 4 to 7. All are MeSH headings.
- The abstract cites nothing and defines every abbreviation it uses.
