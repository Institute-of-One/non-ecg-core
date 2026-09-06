# Step 3 protocol — measuring N_min

Frozen 2026-09-06, before the simulation was written or run. The result of step 2 rests
entirely on one constant and the headline flips between 2.5 and 3.0 cycles, so the constant
is measured against a criterion fixed in advance rather than chosen after seeing the curve.

## The question

`N_min` is the number of cardiac cycles that must be written across the heart before the
cardiac period can be recovered from the cardiac border trace of a helical CT scan.

## Why the estimator is deliberately the best possible one

The estimator below is given the true waveform shape and fits only its period, amplitude,
phase and the anatomical baseline. That is more than any real method knows.

This is on purpose. The claim is a **bound**: if an estimator that already knows the shape
of the signal still needs `N` cycles, then no method that has to discover the shape needs
fewer. A weak estimator would measure the estimator, not the physics.

## Signal model

Along the reformatted z axis, the measured cardiac border position at slice `k` is

```
b(z_k) = baseline(z_k) + a · m(z_k / W + phi) + noise_k
```

- `W = Th · S` — the spatial period, the quantity to be recovered.
- `m` — the cardiac waveform, one period, asymmetric: contraction is faster than filling.
  Two fixed harmonics, `cos(2*pi*u) + 0.35 · cos(4*pi*u + pi/4)`, normalised to unit
  peak-to-peak. A pure sinusoid would be easier than the real thing and would understate
  `N_min`.
- `baseline` — the **confound that makes this a real problem**. The cardiac border moves
  along z for anatomical reasons as well as for cardiac ones: the heart is not a cylinder.
  Modelled as a quadratic in z with amplitude `beta · a`. With many cycles it separates
  from the periodic part easily; with one or two it does not, and that, not noise, is what
  is expected to set `N_min`.
- `noise` — Gaussian, standard deviation `sigma · a`, standing for image noise, partial
  volume and border-detection error together.

## Estimator

Separable nonlinear least squares. For each candidate `W` on a grid spanning 0.3 to 3.0
times the true value, the baseline coefficients, amplitude and phase enter linearly and are
solved exactly; the residual is minimised over `W`, then refined by parabolic interpolation
about the best grid point. The grid is deliberately wide, so a wrong period is a possible
answer rather than an excluded one.

## Sweep

| factor | levels |
|---|---|
| cycles written, `N` | 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0 |
| noise, `sigma` | 0.05, 0.10, 0.20, 0.40 |
| baseline strength, `beta` | 0.0, 0.5, 1.0, 2.0 |
| samples per cycle, `n` | 8, 16, 32 |
| heart-rate variability | 0%, 5%, 10% (standard deviation of successive cycle lengths) |

200 trials per cell, seeded from a fixed root so the whole sweep is reproducible.

## Criterion, fixed now

- A trial **succeeds** when the recovered period is within **5%** of the true period.
- `N_min` for a cell is the smallest `N` on the grid at which the success rate is at
  least **90%**.
- The headline `N_min` is the value under the **central** condition:
  `sigma = 0.10`, `beta = 1.0`, `n = 16`, variability 5%. Every other cell is reported as
  sensitivity, not as an alternative headline.

## What each outcome would mean, decided before seeing it

- **`N_min` <= 2.5** — the step-2 threshold for routine chest CT falls at or below about
  96 bpm, so some resting patients qualify. The paper reports a boundary that ordinary
  practice already crosses part of the time.
- **`N_min` = 3.0** — the threshold is about 115 bpm. No resting patient qualifies on a
  routine protocol; tachycardic ones do. The two windows are disjoint, which is the
  result step 2 anticipated.
- **`N_min` >= 5** — the threshold exceeds 190 bpm and even tachycardia does not bring
  routine protocols inside. The technique is confined to cardiac protocols, and the paper
  is purely a bound on what motion-correction methods can recover.

All three are reportable and none is a failure. Recording that here is the point: an
outcome that would have been called disappointing after the fact cannot be, having been
named in advance.

## What would falsify the whole line

A cardiac period recovered, in real data, from a scan whose parameters place it outside
the window. That observation would show the bound is not a bound, and it should be
reported if it is ever made.
