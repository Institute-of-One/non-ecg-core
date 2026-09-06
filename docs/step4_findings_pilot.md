# Step 4, pilot on real images — what was measured and what was not

Recorded 2026-09-06 under `step4_protocol_real_data.md` (commit `6586bb1`).
Three series, 1004 MB, identified by UID in `results/pilot_series.json`. No imaging is
redistributed and none is committed.

## The first attempt was wrong, and visibly so

The initial extraction returned implied heart rates of 13 to 38 bpm and pulsation
amplitudes of 29 to 102 mm. The cardiac border does not move 100 mm and no patient beats
at 13 bpm, so the numbers refuted themselves.

Two separate defects:

- **the border tracker jumped between structures.** Choosing the widest mediastinal run
  independently at each slice let it wander between aorta, heart, hilum and chest wall:
  168 mm of total swing with twenty jumps over 5 mm, while the median slice-to-slice change
  was 0.00 mm. The signal was there under a handful of catastrophic jumps.
- **the period search reached anatomical scales.** The grid ran to half the scanned length,
  so a 156 mm anatomical envelope beat a 34 mm cardiac oscillation every time.

Both are fixed: the border is now tracked with a continuity constraint, and the period band
is fixed a priori by the header's table speed and by physiology (40 to 120 bpm), not by
what the data prefers. The baseline is quartic — flexible enough for anatomy varying over
100 mm and far too stiff to imitate a 34 mm oscillation.

## What the corrected measurement gives

Amplitudes of 1.6 to 15 mm and residuals of 0.6 to 4.5 mm, which are the right order for a
cardiac border. Validity is judged by the bound's own criterion — at least `N_min` = 2.5
cycles written, the fit not pinned at the edge of the physiological band, and the residual
below the pulsation it sits on.

| series | table speed | threshold | valid levels | median sigma |
|---|---:|---:|---:|---:|
| Anti-PD-1_Lung | 33.6 mm/s | 42 bpm | **4 / 6** | 0.43 |
| RIDER Lung CT | 55.0 mm/s | 69 bpm | **4 / 6** | 0.37 |
| COVID-19-NY-SBU | 78.8 mm/s | 98 bpm | **1 / 6** | — |

**The ordering is what the bound predicts.** The fast protocol collapses — three of its six
levels pin at the edge of the physiological band and two leave a residual larger than the
pulsation — while the two slower ones do not.

**And `sigma` is 0.37 to 0.43**, inside the range the step-3 sweep covered, where `N_min`
stays 2.5. The frozen decision rule's noise branch is satisfied on measurement rather than
on assumption.

## What was not achieved, and must not be reported as if it were

**The recovered heart rate is not consistent across coronal levels** — spreads of 42 and 49
bpm within a single patient. Something periodic is being found in the slow scans and not in
the fast one, but the period is not stable enough to be called a heart rate.

**There is no ground truth.** TCIA carries no heart rate, so even a consistent value could
not be checked against the patient's actual rate. Only internal consistency is testable
here, and internal consistency is currently what fails.

## The cause, and the next estimator

Each coronal level is fitted independently, and different levels cut different structures —
heart at some rows, descending aorta at others — with different amplitudes and phases. But
**the period is common to all of them, because there is one heart.** A joint fit sharing
one period across levels is strictly more powerful than six independent fits, and not
using it was a gap in the design rather than a limitation of the data.

Also to fix: one level returned a 7 635 mm amplitude from a fit with 0.44 cycles. A
degenerate fit must be rejected before it is reported, not after.
