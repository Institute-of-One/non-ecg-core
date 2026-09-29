# Is there a public non-gated helical chest CT with a recorded heart rate?

Added 2026-09-29, **after** the cohort was frozen and fitted, in response to a Physics in
Medicine and Biology board member's observation that the cohort analysis has no reference
heart rate. It is a search of what exists in a public archive, not a decision rule, and
nothing here changes anything that was frozen before the cohort was analysed. Any result
taken from it into the manuscript is post-hoc and is declared as such.

## What it does

Three stages, each narrowing the next:

| script | question | result |
|---|---|---|
| `sweep_bodyparts.py` | which of TCIA's collections hold CT at all, and which hold CT of the heart? | 156 collections; 102 hold CT; 2 hold a series labelled `BodyPartExamined = HEART` |
| `sweep_cardiac_studies.py` | which studies are described as a cardiac examination? | 57 studies, 0 collections failed. `BodyPartExamined` is blank on 553 of 727 CT series in one collection, so the study description is the more reliable key |
| `probe_candidates.py` | for each such patient, does one instance per series show a recorded rate, and a free-running helical series on the same date? | 23 multi-series studies probed, 0 series unreadable |

## What it found

**One session, in the whole archive, carries both.**

`VAREPOP-APOLLO` patient `AP-26JK`, study `CARDIAC CTA`, SOMATOM Definition Flash:

- a gated cardiac series at 09:20:21 (pitch 0.3) recording `OSCRATEMIN072BPM`,
  `OSCRATEMAX078BPM`, `OSCRATEAVG075BPM`
- a free-running helical series `Chin thru Pelvis 2.0 THINS`, 631 images, pitch 1.55,
  59.5 mm per rotation, 285 ms rotation, beginning at 09:20:32 — **ten seconds later**

Measured over the whole series once it was downloaded: z span **630 mm**, table speed
208.7 mm/s, acquisition **3.02 s**, so **3.77 cardiac cycles are written** at the recorded
rate. N_min for the fundamental estimator is 2.5, so this series clears the bound by about
half again — it is not a marginal acquisition.

> An earlier draft of this file put the span at 443 mm and the cycles at 2.65, from the
> first, middle and last instance returned by `getSOPInstanceUIDs`. That order is not
> spatial, so those three instances do not bracket the volume and the figure was a lower
> bound. The values above come from the full series and supersede it. The difference
> matters: at 2.65 cycles a failure would sit close enough to the bound to be ambiguous,
> whereas at 3.77 it does not.

The geometry is self-consistent. Predicting the z position of an instance from the header
table speed and its acquisition time reproduces the header's own value to within 0.1 mm, and
the acquisition-time span across the series equals the z span divided by the table speed. The
scan does convert z into time at a constant rate, which is the premise of the paper,
confirmed here on a real acquisition.

## The rate is not where a reader would look for it

`HeartRate (0018,1088)` is **empty** in every series of that session. Siemens writes the rate
into the free text of `ScanOptions (0018,0022)` instead. A survey that checks only the
standard DICOM cardiac fields concludes that no public CT records the rate, and is wrong.
`analysis/check_cardiac_tags.py` was extended to read both routes after this was found, and
its test carries the Siemens string as an injected defect.

## What this can and cannot support

It is **one case**. It supports a worked demonstration — whether the frozen pipeline recovers
75 bpm from a real non-gated scan whose rate is known — and it cannot support a recovery
rate, an accuracy figure, or any statement about a population.

It is a **lower bound**. The search keys on a study description naming a cardiac examination.
A session that included a cardiac acquisition but was described otherwise is missed, and so
is any archive other than TCIA.

A failure on this case is **not** explained away by a marginal acquisition: at 3.77 written
cycles the scan clears N_min = 2.5 by half again. That is what makes the result reported in
`../../results/reference_case.json` worth having.

## Reproducing

```bash
python analysis/tcia_search/sweep_bodyparts.py         # writes tcia_bodyparts.json
python analysis/tcia_search/sweep_cardiac_studies.py   # reads it, writes tcia_cardiac_studies.json
python analysis/tcia_search/probe_candidates.py        # reads it, writes tcia_pairings.json
```

The third downloads one image per candidate series into `probe_cache/`, which is not part of
this repository: no image data is redistributed here, only headers reduced to the fields
above.
