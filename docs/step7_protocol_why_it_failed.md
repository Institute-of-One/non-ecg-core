# Step 7 protocol — why 3 of 17, when the simulation says it should have worked

Frozen 2026-09-07, before any real trace was compared with any simulated one.

## The discrepancy, stated precisely

It is not a noise-magnitude problem, and that is already established rather than assumed:

- measured sigma on the real traces was **0.37 to 0.43**;
- the step-3 sweep at sigma = 0.40 with 32 samples per cycle gives `N_min` = 2.5;
- the cohort series wrote **4 to 11 cycles**, far above 2.5.

By the simulation these should have recovered. Three of seventeen did. **Something structural
differs between a simulated trace and a real one, and the amplitude of the noise is not it.**

## What this step may and may not conclude

It may identify a property of real traces, measure it, and test whether adding it to the
simulator reproduces the observed failure. It **may not** postulate a mechanism whose only
support is that it would close the gap, and it may not state or imply that some corrected
method would recover a larger fraction. No such claim is available without building that
method and measuring it.

## Candidate properties, named before measuring

Each is measurable on data already held, on all 17 series and their simulated counterparts.

1. **No periodic component at the predicted period.** Periodogram power in the physiological
   band relative to total power in the detrended trace. If real traces carry no excess there,
   the signal is absent from what was extracted, whatever the bound permits.
2. **A baseline the quartic cannot absorb.** Residual variance after the quartic fit as a
   fraction of the raw variance. The simulator's envelope is a quadratic by construction;
   real anatomy may need far more, leaving structure that a periodic term then fits.
3. **Discontinuities.** Number and size of slice-to-slice steps, which mark the tracker
   changing structure rather than following one.
4. **Non-stationarity.** Drift of amplitude or period along z, which a single shared-period
   fit cannot represent.

**The candidate I expect** — recorded now so that finding it is a prediction met and not a
story fitted — is (1), and for a specific reason: **the extractor may not have been looking
at the heart.** The coronal levels were fixed at 0.45 to 0.70 of image height, which is a
geometric convention, not an anatomical one. The left cardiac border sits where it sits in
each patient. If those levels mostly cut chest wall, hilum or aortic wall, the trace is of a
structure that barely pulsates, and no amount of correct sampling theory helps.

If that is the answer, it is a **targeting failure, not biological noise**, and it must be
reported as such.

## What counts as identifying the mechanism, fixed now

Both conditions, not either:

1. **A stated, quantified difference** between real and simulated traces on one of the
   properties above, larger than the spread within each group.
2. **Reproduction.** Adding that property to the simulator, at the measured magnitude, must
   drop the simulated success rate from its present value at the cohort's cycle counts and
   sigma to **within 10 percentage points of the observed 3 of 17 (18 per cent)**.

Condition 2 is what separates a mechanism from a story. A property that differs but does not
reproduce the failure is reported as a difference and nothing more.

## If no candidate reproduces the failure

Then the cause is not among the four, and the paper says exactly that: the discrepancy
between the bound and the cohort is unexplained, four specific explanations were tested and
rejected, and the data to test them is public. **That is a usable result and it is the
honest one.** It is written here so that failing to find a mechanism does not become a
reason to keep looking until something fits.

## Unchanged

The step-5 conclusion stands regardless of what is found here: at current protocols the
sampling bound is necessary and not the binding constraint. Step 7 asks what the binding
constraint is; it cannot revise whether the bound was binding.
