# Reference-rate validation: protocol, frozen before the data were fetched

Written 2026-09-29, **before** the image series was downloaded and before the pipeline was
run on it. Nothing in this file may be changed after the run; a changed criterion invalidates
the test and the run must be repeated under a new protocol with both versions kept.

## Why this test exists

The cohort analysis scores a self-consistency criterion, not correctness, because no series
in the cohort records the patient's heart rate. A Physics in Medicine and Biology board
member identified the same gap. A survey of all 156 TCIA collections (see `README.md`) found
exactly one public session containing both a recorded rate and a free-running helical series:
this one. It is the only test of its kind available without a scanner.

## The case

- Collection `VAREPOP-APOLLO`, patient `AP-26JK`, study `CARDIAC CTA`
- Series under test: `1.3.6.1.4.1.14519.5.2.1.264532322608206684963835753501167761257`
  (`Chin thru Pelvis 2.0 THINS`, 631 images, pitch 1.55, 59.5 mm per rotation, 285 ms
  rotation, acquisition begins 09:20:32)
- Reference rate, from the gated series of the same session acquired ten seconds earlier
  (`OSCRATEMIN072BPM`, `OSCRATEMAX078BPM`, `OSCRATEAVG075BPM`): **75 bpm, recorded range
  72–78 bpm**

## What will be run

`run_cohort.analyse_series(directory)`, **unmodified**, on the downloaded series. No
parameter, threshold or code path of the frozen pipeline is altered for this case. The
function is the same one that produced the cohort outcome.

## The criterion

**Primary outcome — is the fitted rate correct?**
The fitted `heart_rate_bpm` is in agreement if it falls within **±5 per cent of 75 bpm**,
that is within **71.25 to 78.75 bpm**. Outside that interval is a disagreement.

The tolerance is not chosen for this case. Five per cent is the tolerance under which N_min
was measured in the simulation (`results/n_min_fundamental.json`, `criterion.tolerance =
0.05`), and it is also, to within a per cent, the width of the rate range the scanner
actually recorded during the session (72–78 bpm is ±4 per cent of 75).

**Secondary outcome — does the frozen self-consistency criterion admit the series?**
Reported as `recovered` by the unmodified function: leave-one-out spread at most 10 bpm,
median sigma below 1.0, at least three usable levels, not pinned at the band edge, at least
N_min = 2.5 cycles written.

**The comparison that matters** is the pair. Four outcomes are possible and all four will be
reported as found:

| | rate correct | rate wrong |
|---|---|---|
| **self-consistent** | the criterion means what the paper implies | the criterion is confidently wrong — the most important negative |
| **not self-consistent** | the criterion is conservative | uninformative |

**Technical failure** is any return carrying `technical_failure`, or a download that does not
yield a readable volume. It is reported as such and is not counted as either outcome.

## What this case can and cannot support

It is one series. It supports a statement about this series and no recovery rate, accuracy
figure or population claim.

Its margin above the bound is thin. From its own headers the z span is 443 mm at 208.8 mm/s,
so 2.55 to 2.76 cycles are written across the recorded rate range, against N_min = 2.5.
**A disagreement here is therefore weakly diagnostic**: it is consistent with the bound being
correct and the acquisition marginal, as well as with the extraction being inadequate. An
agreement is the stronger of the two possible results, because it would show recovery working
at the boundary the paper derives.

The reference rate is from a series acquired ten seconds earlier, not from this one. The
recorded 72–78 bpm range is the scanner's own measure of how much the rate moved during that
acquisition, and it is carried into the tolerance rather than ignored.

## Declared status

Post-hoc. This case was chosen after the cohort was frozen, analysed and written up, and it
was chosen because it is the only one with a reference rate. It is reported as a separate
test with its own protocol, never merged into the cohort, and the manuscript and cover letter
state that it was added in response to editorial feedback.

A local file is not an independent timestamp. This protocol is only evidence of having been
frozen first once it is pushed to the public repository; that was the lesson of the inquiry
of 2026-09-07, and it applies here.
