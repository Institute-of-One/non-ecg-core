# Writing rules for the IORN-011 manuscript

Decisions made before the prose, so they are not re-argued while writing.

## The hand-off is made by facts, never by a request

The paper's practical role is to make a definitive study possible: one on chest CT where
the heart rate was recorded at acquisition. That role is served by supplying the criterion,
not by asking anyone to use it.

**Do not write** any sentence of the form "future clinical studies should validate this",
"a prospective study recording heart rate would confirm", or "we hope others will".

A request like that invites the reviewer's reflex -- *then do it yourself* -- and it is
hard to answer. The expected value is one-sided: written, it risks the paper now; unwritten,
whoever eventually runs that study cites this one for the bound. The role is discharged
either way.

**Do write**, because both are measurements or rigour rather than requests:

- **No public chest or cardiac CT carries a recorded heart rate.** 43 series checked, none.
  Stated as a finding about the state of validation in the field. A reader who runs a CT
  service draws the obvious conclusion without being told it.
- **The falsification condition**, already frozen: a cardiac period recovered, in real data,
  from a scan whose parameters place it outside the window would show the bound is not a
  bound. This is not a demand on the reader; it is what makes the claim testable.

## Section order: the reader meets the strongest result before the failure

Theory -> the constant -> real protocols -> **learned estimator** -> cohort and the open
question -> discussion.

The cohort moved after the learned-estimator result. This was checked for rationalisation
and stands on structure: the bound and the learned estimator are about what an acquisition
*contains*; the cohort is about whether one particular extractor could *read* it, which is
logically subordinate. Every number from the cohort is reported in full either way.

## Two negatives, reported as two negatives

The paper contains a failed practical route (3 of 17) and a failed search for its cause
(four candidates, none reproducing). Both are stated plainly and neither is softened. What
is not permitted is proposing a mechanism, or suggesting that some corrected method would
recover more; neither is available from this data, and step 7 tested and rejected the one
property that separated.

## No number may be typed

Every quantity comes from `paper/frozen/manifest.json` through a marker. A quantity absent
from the manifest may not be asserted. This applies to the cover letter and any
correspondence as well -- it was already breached once, in the PMB inquiry, and caught.
