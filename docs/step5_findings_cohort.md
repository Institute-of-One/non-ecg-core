# Step 5 findings — the cohort, and the outcome the protocol named

Recorded 2026-09-06 under `step5_protocol_cohort.md` (commit `d82f797`), which fixed both
the prediction and the success criterion before either was computed on the cohort.

## Result

18 series, 17 analysed, 1 technical failure (no usable coronal levels).

**3 of 17 recovered a period. Agreement between prediction and outcome is 5/17, 29 per
cent — worse than chance.**

| | recovered | failed |
|---|---:|---:|
| predicted recoverable (threshold <= 100 bpm) | 2 | 11 |
| predicted not recoverable | 1 | 3 |

Twelve series were predicted recoverable and two of them were. Seven failures pinned at the
edge of the physiological band, which is the signature of no periodic signal; the rest were
unstable, moving 12 to 72 bpm when a single coronal level was dropped.

The one series that recovered against prediction, CPTAC C3N-00704 at 137.5 mm/s, returned
75 bpm while its own threshold is 172 bpm. It should not have been recoverable, which makes
a spurious fit the likely reading rather than a point in the method's favour.

Sensitivity to the calibrated stability threshold changes nothing: at 5, 10 and 20 bpm the
recovery counts are 2, 3 and 4 of 17 and agreement is 35, 29 and 24 per cent.

## The preregistered interpretation, applied

The frozen protocol named three outcomes. This is the third:

> *Recovery is rare everywhere, including where predicted. The signal is not extractable
> from the cardiac border by this method at this noise level. The theory stands, the route
> does not, and the paper reverts to the sampling-limit framing with the cohort as the
> evidence that the practical route was tried.*

That is applied as written.

## The pilot was misleading, and it was the pilot's job not to be

Three series gave one clean recovery, one unstable fit and one predicted failure, and that
pattern read as support. It was not. The two Anti-PD-1 series still recover — 50 and 48 bpm,
spreads of 4.0 and 1.3 bpm — but at 3 of 17 they are the exception, and nothing in the pilot
distinguished them from the eleven predicted successes that failed.

Nothing was changed after seeing the cohort. The criterion, the estimator and the coronal
levels are the ones frozen beforehand.

## What survives

- **The window and the budget identity.** Arithmetic; untouched by this.
- **`N_min` = 2.5**, bracketed 1.5 to 2.5 by estimator class over 144 simulated cells.
- **The protocol distribution.** 192 series of real headers, table speeds 30.0 to 158.8 mm/s.
  What a scan *could* carry is unaffected by whether this extractor could read it.
- **The wide-detector and high-pitch impossibility**, at 864 and 1843 bpm.

## What does not

**Recovering the cardiac period from the left mediastinal border of a routine non-gated
chest CT.** Not at 3 of 17, and not with a prediction that carries no discriminating power.

The failure is of this extraction method rather than of the physics, and that distinction is
real — but it is not an excuse, because no evidence exists that another method would do
better. Anything further would be a new study with its own registration.

## What this does to the paper

The constructive framing of step 4 — that ordinary chest CT already records a usable cardiac
period — is not supported and is withdrawn. The paper returns to what it can carry: a
sampling bound on what a non-gated acquisition can contain, measured against real protocol
parameters, with a cohort showing that the most obvious practical route to reading it does
not work.

That makes the bound more useful to state, not less. A method claiming to recover cardiac
phase from these scans now has something concrete to beat.
