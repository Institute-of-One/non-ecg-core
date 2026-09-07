# Step 7 findings — four explanations tested, none reproduces the failure

Recorded 2026-09-07 under `step7_protocol_why_it_failed.md` (commit `9a660af`), which named
the four candidates, the expected one, and what would count as identifying a mechanism,
before any real trace was compared with a simulated one.

## Result

**None of the four candidates reproduces the observed failure.** The discrepancy between
what the bound permits and what the cohort delivered is unexplained.

| candidate | real vs simulated | separated? | reproduces 3/17? |
|---|---|---|---|
| no periodic component in the band | enrichment 7.2 vs 9.0 | no | — |
| baseline the quartic cannot absorb | sub-band residual 0.119 vs 0.009 | no | — |
| discontinuities | 0.000 vs 0.000 | no | — |
| non-stationarity | drift 1.47 vs 1.04 | no | — |
| *(baseline magnitude)* | share 0.880 vs 0.124 | **YES** | **no** |

## The one property that separated, and why it is not the cause

Baseline share — the fraction of trace variance the quartic absorbs — is 0.880 in real
traces against 0.124 in simulated ones, with no overlap between the middle 80 per cent of
each population. It was the obvious candidate.

It fails the reproduction test outright. Raising the simulator's envelope to match it
(`beta` = 8.0, share 0.886) leaves the simulated success rate at **100 per cent**, and so
does going further, to share 0.969. The reason is plain in hindsight: the simulator's
envelope is a low-order polynomial and the quartic removes it exactly, however large it
grows. **Magnitude was never the difficulty; shape would have been, and the simulator has
none.**

## Two defects in this step's own execution, recorded

- **The predicted candidate was wrong.** The protocol recorded an expectation that real
  traces would carry no periodic component at the predicted period, because the coronal
  levels were fixed geometrically rather than anatomically and might not be cutting the
  heart at all. They do carry one: band enrichment is 7.2 against a flat spectrum, close to
  the simulated 9.0. The heart is visible in these traces. The prediction is recorded as
  met or not, and it was not.
- **Candidate 2 was first measured with the wrong instrument.** `baseline_share` measures
  what the quartic *did* absorb, not what it could not, so the candidate as written went
  untested until the residual was split by frequency region. That correction is why the
  "none of the four" conclusion is being drawn now and not two steps earlier.

## What the numbers do say

Real traces do not differ from simulated ones by a shift. They differ by **spread**.

| | 10th-to-90th range, in-band power fraction |
|---|---|
| real border traces | **0.625** |
| simulated traces | **0.083** |

Roughly seven and a half times wider. Some real traces are indistinguishable from
simulation; most depart from it, and in different directions.

**There is no single property separating real traces from simulated ones. Real data carries
a heterogeneity the simulator does not have.**

That is consistent with the step-5 result rather than merely compatible with it. If the
failure mode varies from series to series, no single quantity computed from a header can
predict which series will fail — which is exactly what was observed, and why agreement was
no better than chance.

## What the manuscript may say

That four specific explanations were tested against a criterion fixed in advance and none
reproduces the failure; that the one separating property does not cause it, with the
reproduction test shown; that real traces are heterogeneous where simulated ones are not;
and that the discrepancy is therefore open.

**It may not** propose a mechanism, and it may not suggest that some corrected method would
recover a larger fraction. Neither is available from this data.

## Unchanged

Step 5 stands: at current protocols the sampling bound is necessary and not the binding
constraint. Step 7 asked what the binding constraint is and did not find out.
