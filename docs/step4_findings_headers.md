# Step 4, first result — real protocols, from headers only

Recorded 2026-09-06, under `step4_protocol_real_data.md` (commit `6586bb1`). No image was
opened for this: one slice per collection was fetched and its header read.

## Which public collections can answer the question at all

The window is a condition on table speed, and table speed comes from tags that many
archives no longer carry. This is invisible until a header is opened, and it decides which
collection can support the paper.

| collection | scanner | spiral parameters |
|---|---|---|
| LIDC-IDRI | Sensation 64, syngo 2006A | **none** |
| NSCLC-Radiomics | — | none |
| NSCLC Radiogenomics | — | none |
| LungCT-Diagnosis | — | none |
| TCGA-LUAD | — | none |
| SPIE-AAPM Lung CT Challenge | — | none |
| COVID-19-AR | — | none |
| QIN LUNG CT | LightSpeed VCT | **present** |
| CPTAC-LUAD | Discovery IQ | **present** |
| COVID-19-NY-SBU | Aquilion ONE | **present** |
| Anti-PD-1_Lung | SOMATOM Definition Flash | **present** |
| RIDER Lung CT | LightSpeed16 | **present** |
| Lung-PET-CT-Dx | Biograph 64 | **present** |

**LIDC-IDRI, the collection this step was planned around, carries none of them.** Its
acquisition module stops at slice thickness, kVp, tube current and exposure time. It
remains suitable for measuring the aortic signal, where the tags are not needed, but it
cannot say where practice sits. The protocol named it before a header had been opened;
that choice is now made on evidence.

## What the surviving headers say

| collection | pitch | table speed | threshold, cardiac border (L=120 mm) | threshold, aorta (L=300 mm) |
|---|---:|---:|---:|---:|
| Anti-PD-1_Lung | 0.5 | 33.6 mm/s | **42 bpm** | 17 bpm |
| Lung-PET-CT-Dx | 1.0 | 38.4 mm/s | **48 bpm** | 19 bpm |
| CPTAC-LUAD | 1.375 | 45.8 mm/s | **57 bpm** | 23 bpm |
| RIDER Lung CT | 1.375 | 55.0 mm/s | **69 bpm** | 28 bpm |
| QIN LUNG CT | 1.375 | 110.0 mm/s | 138 bpm | 55 bpm |
| COVID-19-NY-SBU | 0.806 | 129.0 mm/s | 161 bpm | 64 bpm |

At `N_min = 2.5`.

## Two of my assumptions were wrong, both in the same direction

Step 2 used a single textbook protocol, 64 x 0.6 mm at pitch 1.0, giving 76.8 mm/s. Real
chest protocols span **33.6 to 129 mm/s** — a factor of four — and the slow half is not
unusual practice but ordinary oncology and immunotherapy follow-up imaging.

So both quantities step 2 assumed were wrong, and both were pessimistic:

- `N_min` assumed 3, measured 2.5;
- table speed assumed 76.8 mm/s, measured as low as 33.6 mm/s.

**Four of six real protocols record a recoverable cardiac period at the cardiac border
alone, at thresholds of 42 to 69 bpm** — below the resting heart rate of most patients.
The aortic route is not needed for those; it is what makes the remaining two work as well,
bringing every one of the six inside at 17 to 64 bpm.

## What this does to the paper

The limits framing of step 2 does not survive contact with real protocol parameters. What
survives, and is now supported rather than assumed:

- the window and the budget identity, unchanged;
- `N_min` bracketed at 1.5 to 2.5 by estimator class;
- the wide-detector and high-pitch impossibility, unchanged and untouched by this;
- **and the constructive result: ordinary chest CT already records the cardiac period, in
  most of the protocols public archives actually contain.**

## Still to do

- The aortic signal itself: the amplitude against border-detection precision, which is the
  one thing needing images rather than headers, and the decision rule for it is already
  frozen.
- A larger header harvest across these six collections, to replace six single series with
  a distribution.
- The pulse-wave phase delay along the descending aorta.

## The sweep, crossed against the real headers

The 144-cell sensitivity sweep for the headline estimator finished after the harvest, and
the two together say something neither says alone.

`N_min`, worst case over baseline strength and rhythm variability:

| | 8 samples/cycle | 16 | 32 |
|---|---:|---:|---:|
| sigma 0.05 | 2.5 | 2.5 | 2.5 |
| sigma 0.10 | 2.5 | 2.5 | 2.5 |
| sigma 0.20 | 3.0 | 2.5 | 2.5 |
| sigma 0.40 | 3.5 | 3.0 | **2.5** |

116 of the 144 cells give 2.5 exactly. `N_min` degrades only where the waveform is coarsely
sampled, and every real protocol is far from that: at 60 bpm they give **33 to 129
reconstructed samples per cardiac cycle**.

**So the noise branch of the frozen decision rule is closed before the images are opened.**
Whatever the measured `sigma` turns out to be, up to 0.40, `N_min` stays at 2.5 for these
protocols, because all of them sit in the well-sampled regime.

This is the budget identity showing up in practice. `N x n = L / dz`, and real chest
protocols spend that budget lopsidedly: enormous resolution within each cycle, and very few
cycles. They are not short of detail about the waveform. They are short of waveform. The
lever that helps is therefore not a finer reconstruction but a longer `L`, which is exactly
what the aortic route buys.
