# non-ecg-core (IORN-011)

Cardiac period estimation from non-gated helical CT: sampling criteria and exploratory evaluation.

A helical CT moves the table at a constant speed, so the z axis of the reconstructed
volume is also a time axis with a known scale. A periodically moving structure writes its
period into the image as a spatial period along z:

```
W = Th x S,     S = pitch x total collimation / rotation time
```

`S` is computable from the DICOM header of any helical acquisition. This repository asks
when `Th`, the cardiac cycle, can be recovered from `W` in a scan acquired without an
electrocardiogram, derives a sampling bound for it, tests the bound in simulation and on
public TCIA acquisitions, and examines what a learned estimator does beyond it.

The work is simulation and public data only. No imaging is redistributed: series are
identified by collection, public patient ID and SeriesInstanceUID in `results/`, so every
measurement can be repeated from The Cancer Imaging Archive.

## How the work was done

Each step was written as a protocol, with its decision rule, and committed before the
data or simulation it governs was run; its findings were committed afterwards as a
separate file. `git log --follow docs/<file>` shows the order.

| Step | Protocol | Findings |
|---|---|---|
| 1-2 Prior art, feasibility | | `FINDINGS.md`, `novelty/` |
| 3 Simulation, `N_min` | `docs/step3_protocol.md`, `docs/step3_protocol_amendment_v1.1.md` | `docs/step3_findings.md` |
| 4 Real headers and pilot | `docs/step4_protocol_real_data.md` | `docs/step4_findings_headers.md`, `docs/step4_findings_pilot.md` |
| 5 Cohort | `docs/step5_protocol_cohort.md` | `docs/step5_findings_cohort.md` |
| 6 Learned estimator | `docs/step6_protocol_learned_estimator.md` | `results/learned_estimator.json` |
| 7 Why recovery failed | `docs/step7_protocol_why_it_failed.md` | `docs/step7_findings_why_it_failed.md` |

The commits were made locally between 2026-09-06 and 2026-09-07, and the repository was
first made public on 2026-09-18. Commit timestamps are recorded by the author's machine,
so they document the order of the work but are not an independent time-stamp.

## Contents

| Path | What it is |
|---|---|
| `analysis/` | Sampling bound, simulation sweep, border-trace extraction, joint period fit, learned estimator, failure diagnosis |
| `data/` | Scripts that probe TCIA collections, harvest headers, and fetch the pilot and cohort series into an ignored local cache |
| `results/` | Every measured and simulated result the findings cite |
| `novelty/` | The prior-art search, its queries and the records it returned |
| `paper/` | The manuscript in progress and the frozen-result manifest |

## Status

The manuscript is in preparation and has not been submitted. Its results sections still
contain unresolved markers.

## Licence

MIT, see `LICENSE`. The TCIA collections used are distributed under their own licences,
recorded per series in `results/`.
