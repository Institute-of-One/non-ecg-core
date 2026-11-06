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

**BACKGROUND:** Cardiac motion marks the mediastinal border of a non-gated chest CT; a recoverable period would sort it by phase.

**OBJECTIVE:** To state the conditions that make the period recoverable, and how far an image estimate can be trusted.

**METHODS:** The cycles needed were measured over [[results:manifest.json:metrics.sensitivity_cells]] simulated conditions, applied to [[results:manifest.json:metrics.header_series]] real series by header, and tested on [[results:manifest.json:metrics.cohort_analysed]] image series under a frozen criterion.

**RESULTS:** Cycles written and samples per cycle multiply to L/dz, so speed only divides a fixed budget. The threshold is [[results:manifest.json:metrics.n_min_fundamental]] cycles, [[results:manifest.json:metrics.n_min_matched]] matched, empirical not universal. At an assumed cardiac extent, [[results:manifest.json:metrics.records_below_100bpm_border_percent]] per cent of real series meet it below [[results:manifest.json:metrics.prediction_ceiling_bpm]] bpm. On images [[results:manifest.json:metrics.cohort_recovered]] of [[results:manifest.json:metrics.cohort_analysed]] met the criterion, their cost minima no deeper than the rejections'.

**CONCLUSIONS:** Whether a scan can carry cardiac timing follows from its header, before any image is analysed. A period estimated from images should not be accepted on self-consistency alone: no level of the admitted series tracked the intended border throughout, and re-counting over the stretch where it did put one of the three below the cycle threshold. Before clinical use a period needs the depth of its minimum and a check of what was tracked.

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
