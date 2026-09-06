# Step 4 protocol — what real data is for, and what it is not for

Frozen 2026-09-06, before any image was downloaded or looked at.

## Why real data enters at all

Steps 1 to 3 need none. The relation, the window, the budget identity and `N_min` are
theory and simulation, and adding images to them would not make them truer.

Step 3's constructive result does need it. The claim is that the cardiac period is
recoverable from a routine chest CT **if the signal is taken from the pulsating aorta over
the whole scanned length rather than from the cardiac border over 120 mm**, which drops the
threshold from 96 to about 38 bpm at no additional dose. That claim rests on three
quantities a simulation cannot supply:

- the amplitude of aortic wall motion relative to the precision with which its border can
  be located in an ordinary reconstruction — the noise term `sigma`;
- whether the anatomical envelope of the aorta along z behaves like the low-order baseline
  the simulator subtracts, or defeats it;
- the size of the pulse-wave phase delay along the descending aorta.

Simulating all three would be simulating this analysis's own assumptions.

**This is the lesson of the 2003 manuscript this work descends from.** Its reviewer wrote
that validation used "a very non-clinical situation with optimal object symmetry (a
balloon) and optimal circular attenuation symmetry (cylindrical water bath)". A quadratic
baseline and white noise is the same idealisation wearing different clothes.

## What the data is for, and what it is not

| purpose | real data |
|---|---|
| measure `sigma` empirically | **yes** |
| show that the aortic wave exists in an ordinary reconstruction — one figure | **yes** |
| measure the phase delay along the descending aorta | **yes** |
| harvest protocol parameters from headers, no images, to say where practice sits | **yes** |
| validate the sampling bound | no — it is theory |
| measure `N_min` | no — that is step 3 |
| demonstrate clinical usefulness | **explicitly not.** That framing is what sank the 2003 submission and it is not attempted here |

The paper must state this division in its methods. Real data calibrates an input; it is not
offered as evidence for the bound.

## Source and selection

**LIDC-IDRI** (TCIA), chosen because it is public, permissively licensed, thin-slice, and
**non-contrast** — if the aortic wave is measurable without contrast the claim is stronger,
and if it is only measurable with contrast that is a finding worth reporting rather than
hiding.

Selection, applied to headers before any image is opened:

- helical acquisition carrying `SpiralPitchFactor (0018,9311)`, `RevolutionTime
  (0018,9305)` and `TotalCollimationWidth (0018,9307)`, or enough to derive table speed;
- reconstruction interval <= 1.25 mm;
- descending aorta present over >= 150 mm of the scanned range.

Pilot of 3 to 5 series first, to establish the pipeline and a first `sigma`. No case is
excluded after its trace has been seen.

## The decision rule, fixed now

Let `sigma_measured` be the median across the pilot of the aortic border residual after the
baseline fit, divided by the peak-to-peak pulsation amplitude.

- **`sigma_measured` <= 0.20** — inside the range already swept in step 3, where
  `N_min = 2.5` holds. The constructive result stands: a routine chest CT records a
  recoverable period in the aorta at resting heart rates. This becomes the paper's headline.
- **`0.20 < sigma_measured <= 0.40`** — the upper end of the swept range. The result stands
  only if the step-3 sweep shows `N_min` unchanged at `sigma = 0.40`; the sweep now running
  will already have answered this, and its answer is used as it stands rather than re-run.
- **`sigma_measured > 0.40`** — outside anything measured. The sweep is extended to the
  measured value before any claim is made, and if `N_min` rises enough to push the
  threshold above resting rates, **the paper reverts to the limits framing of step 2** and
  reports that the aortic route was tried and did not close the gap.

The third outcome is a real possibility and is not a failure. Writing it down now is what
stops it from being read as one later.

## Governance

LIDC-IDRI is public and de-identified under its stated licence; no review board approval is
required and none is implied. The collection DOI, the TCIA citation and the licence are
recorded with the results. **No imaging is redistributed** — series are identified by UID.

This has nothing to do with the 2003 material. That data was acquired at another
institution with other investigators and is neither used nor referenced.
