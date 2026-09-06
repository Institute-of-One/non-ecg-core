# Step 3 protocol, amendment v1.1 — bracketing N_min from both sides

Frozen 2026-09-06, after the preregistered central measurement and before the unmatched
estimator was written. It records what the first measurement showed, why that is not yet
an answer, and what is being added.

## What the frozen protocol measured

Central condition, matched estimator: **N_min = 1.5**. Worst adverse cell tested
(noise 0.40, baseline 2.0, variability 10%): **N_min = 2.5**.

Both fall in the band the protocol named as "some resting patients qualify". The
assumption carried through step 2, `N_min = 3`, is **contradicted by the measurement**.
That assumption was mine and it was not measured; this is what freezing the criterion in
advance was for.

## Why this is a floor and not an answer

The estimator fits `cos(2*pi*u), sin(2*pi*u), cos(4*pi*u), sin(4*pi*u)` and the simulated
waveform is a sum of exactly those four terms. The model does not merely know the shape
approximately — the truth lies exactly inside its span. Seven parameters are fitted to as
few as 24 samples, and they succeed because the model is exactly right.

The protocol's reasoning still holds: no method that has to discover the waveform can need
fewer cycles than one handed it. So **1.5 is a valid lower bound on N_min**. It is simply
too low to decide the question, because the interesting region begins around 2.5.

Reporting 1.5 as the answer would be the mistake this whole design exists to prevent: it
would measure the estimator, not the physics.

## What is added

Two further estimators, so the answer is bracketed rather than bounded from one side only.
The signal model, sweep, criterion, trial count and seeds are unchanged.

| estimator | model fitted | what it stands for |
|---|---|---|
| `matched` (already run) | two harmonics, free amplitudes and phases | the floor: the truth is in its span |
| `fundamental` | one harmonic, free amplitude and phase | a method that assumes periodicity but not shape |
| `autocorrelation` | none; first prominent peak of the detrended autocorrelation | a method that assumes only that something repeats |

All three keep the quadratic baseline, because the anatomical envelope is part of the
problem and not part of the estimator's ignorance.

## What each outcome would mean, decided before seeing it

Let `N_real` be the value under `fundamental`, which is the closest of the three to a
method someone would actually write.

- **`N_real` <= 2.0** — the threshold for a routine chest protocol is at or below about
  77 bpm. Ordinary chest CT records a recoverable cardiac period in most patients. The
  paper is then an opportunistic-measurement result, and the step-2 framing as a limit on
  motion correction is wrong and must be dropped.
- **`2.0 < N_real <= 3.0`** — the threshold lands between about 77 and 115 bpm, inside the
  spread of resting heart rates. The paper is about a boundary that runs through ordinary
  practice, and which patients fall on which side becomes the interesting question.
- **`N_real > 3.0`** — the threshold exceeds 115 bpm. The step-2 framing survives: routine
  protocols are too fast for a resting heart, and the result constrains what motion
  correction can recover.

The middle outcome is the one that would need the most care to report and is the one this
amendment most expects. Naming it now is the point.

## What does not change

The falsification condition is unchanged: a cardiac period recovered, in real data, from a
scan whose parameters place it outside the window.
