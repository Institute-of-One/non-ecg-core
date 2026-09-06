# Step 3 findings — N_min measured

Recorded 2026-09-06, against the criterion frozen in `step3_protocol.md` (commit `0758d74`)
and the estimators added in `step3_protocol_amendment_v1.1.md`.

## The measurement

Central condition: noise 0.10, baseline 1.0, 16 samples per cycle, 5% heart-rate
variability. 200 trials per point, period recovered to within 5%, `N_min` is the smallest
number of cycles reaching 90% success.

| cycles written | matched | fundamental | autocorrelation |
|---:|---:|---:|---:|
| 1.0 | 15.5% | 0.5% | 0.0% |
| 1.5 | **92.5%** | 19.5% | 20.5% |
| 2.0 | 100% | 87.5% | **100%** |
| 2.5 | 100% | **100%** | 99.5% |
| 3.0 and above | 100% | 100% | 100% |

```
N_min (matched)         = 1.5     floor: the truth lies in the model's span
N_min (autocorrelation) = 2.0     assumes only that something repeats
N_min (fundamental)     = 2.5     the headline: assumes periodicity, not shape
```

The three agree to within one grid step, which is the useful part. `N_min` is not sensitive
to how much the estimator is told; it is set by the problem.

## What it means, by the rule fixed in advance

`N_real = 2.5` falls in the amendment's middle band: *"the threshold lands between about 77
and 115 bpm, inside the spread of resting heart rates. The paper is about a boundary that
runs through ordinary practice, and which patients fall on which side becomes the
interesting question."*

| protocol | table speed | recoverable heart rates |
|---|---:|---|
| 2003 4-row, row-pitch 6 (the original) | 6.0 mm/s | 8 – 90 bpm |
| **2026 routine chest, 64 x 0.6, pitch 1.0** | 76.8 mm/s | **96 – 576 bpm** |
| 2026 lung screening, pitch 1.2 | 92.2 mm/s | 115 – 691 bpm |
| 2026 wide detector, 192 x 0.6, pitch 1.5 | 691 mm/s | 864 – 8640 bpm |
| 2026 dual-source high pitch | 1475 mm/s | 1843 – 18432 bpm |
| cardiac CT, retrospective gating | 27.4 mm/s | 34 – 343 bpm |

## Two assumptions that were wrong, and one that was not

- **`N_min = 3` was wrong.** It was carried through step 2 as a Nyquist-plus-margin
  assumption and the measurement puts it at 2.5. Freezing the criterion first is what
  makes that a correction rather than a choice.
- **"Modern routine CT is too fast" was wrong**, or at least too broad. A routine chest
  protocol records a recoverable period above 96 bpm, which is not an exotic heart rate in
  a patient lying on a CT table in pain or short of breath.
- **The wide-detector and high-pitch results stand.** 864 and 1843 bpm are not
  physiological by any reading of the constants. On those protocols the period is not
  recorded, and no method can recover what was never written.

## The finding that makes this worth publishing

The heart rates at which a routine scan records the period are the *high* ones — and high
heart rate is also what makes cardiac motion artefact worst. Raising the rate shortens the
spatial period, which writes more cycles into the same scanned length, while at the same
time moving the heart further during each rotation.

**The scans that most need motion correction are the ones that contain the timing needed to
do it honestly.** The scans where a generative model would have to invent the motion are
the fast, wide-detector acquisitions where the artefact is mildest to begin with.

That turns a prohibition into a discriminator. The bound does not say motion correction is
impossible; it says which scans support recovery and which only support synthesis, and the
test is three numbers from the DICOM header plus the patient's heart rate.

## Still outstanding

- The full sensitivity sweep was launched for the `matched` estimator only. It must be
  re-run for `fundamental`, which is the headline estimator, before the sensitivity table
  can be reported.
- `L`, the craniocaudal extent of the heart, is fixed at 120 mm throughout. The threshold
  is inversely proportional to it, so a 100–140 mm range moves the routine-chest threshold
  from 115 to 82 bpm. This matters as much as `N_min` and has not yet been swept.
- Nothing here has touched real data. The falsification condition is unchanged: a cardiac
  period recovered from a scan whose parameters place it outside the window.
