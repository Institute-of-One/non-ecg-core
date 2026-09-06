# Step 5 protocol — what counts as a recovered period, across the cohort

Frozen 2026-09-06, before the joint fit was run on any series beyond the three pilots.

## The question

The bound predicts which scans can carry a recoverable cardiac period. The cohort tests
that prediction: **do the series the bound says should work, work — and do the ones it says
should not, fail?**

That is a claim about agreement between a prediction and an outcome, so both have to be
defined before either is computed on the cohort.

## The prediction, computed from the header alone

For each series, the threshold heart rate is

```
T = 60 x S x N_min / L,     N_min = 2.5 (measured in step 3),  L = analysed z extent
```

A series is **predicted recoverable** when `T <= 100 bpm`, on the grounds that a patient
lying on a CT table is rarely slower than that ceiling allows. 100 bpm is a stated
convention, not a measurement, and the analysis is reported against 80, 100 and 120 bpm so
the reader can move it.

## The outcome, computed from the images

One period is fitted jointly across the coronal levels of a series, sharing the period and
letting amplitude and phase vary per level, because there is one heart and every level
shares the same z-to-time mapping. A series counts as **period recovered** when all four
hold:

1. the joint fit is **not pinned** at either edge of the physiological band (40 or 120 bpm)
   — pinning means the fit wanted to leave the band, which is the signature of no periodic
   signal rather than of a very fast or very slow heart;
2. at least **`N_min` = 2.5 cycles** are written across the analysed extent;
3. the **leave-one-level-out spread is 10 bpm or less** — the estimate must not depend on
   which levels were used;
4. the **median sigma across levels is below 1.0** — the residual must sit below the
   pulsation it is a residual of.

**Condition 3's threshold comes from the pilot and is therefore calibrated, not
independent.** In the three pilot series the spreads were 4, 42 and 4 bpm, and 10 separates
them. This is stated plainly rather than presented as a principled value, and the cohort
result is reported at 5, 10 and 20 bpm so the choice is visible.

## What each outcome would mean, decided now

Let `A` be the series predicted recoverable and recovered, and `D` those predicted not
recoverable and not recovered. Agreement is `(A + D)` over all series.

- **Agreement is high, and the failures fall where predicted.** The bound is doing work: a
  header-computable quantity says in advance which scans carry cardiac timing. This is the
  paper's central empirical claim and the constructive framing stands.
- **Recovery is common but unrelated to the prediction.** Something periodic is being found
  regardless of table speed, which would suggest the estimator is fitting anatomy rather
  than pulsation. The bound would survive as theory and the measurement would not support
  it; that must be reported as such.
- **Recovery is rare everywhere, including where predicted.** The signal is not extractable
  from the cardiac border by this method at this noise level. The theory stands, the route
  does not, and the paper reverts to the sampling-limit framing with the cohort as the
  evidence that the practical route was tried.

The second outcome is the one that would be easiest to misread as success, because a high
recovery rate looks good in isolation. **Agreement with the prediction, not the recovery
rate, is the primary outcome.** Recording that here is the point.

## What is not claimed

There is no ground truth. TCIA carries no heart rate, so a recovered period cannot be
checked against the patient's actual rate. Every statement is about internal stability and
about agreement with a prediction made from the header — never about accuracy.

## Fixed before running

- All 18 cached series are analysed. None is excluded after its fit has been seen.
- A series that fails to load, or yields fewer than three usable coronal levels, is recorded
  as a technical failure and reported separately from a prediction failure.
