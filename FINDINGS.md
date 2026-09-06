# IORN-011 — feasibility, steps 1 and 2

Recorded 2026-09-06. This file says what was checked, what it showed, and what is not yet
established. It is written so that the "no prior work states this" claim can be disputed
by re-running the search rather than by taking anyone's word.

## The idea, in one relation

A helical CT scan moves the table at a constant speed, so the z axis of the reconstructed
volume is a time axis with a known scale. A periodically moving structure writes its
period into the image as a spatial period along z:

```
W = Th x S,     S = pitch x total collimation / rotation time
```

`W` is the distance between successive cardiac peaks in a coronal reformat, `Th` the
cardiac cycle, `S` the table speed — all three of the parameters on the right are in the
DICOM header of any helical acquisition. Read forward, this chooses a protocol. Read
backward, it recovers `Th` from an image acquired for some other purpose, at no additional
dose, with no electrocardiogram.

This descends from an unpublished 2003 manuscript by the same author. Nothing from that
work is reused here: no data, no figures, no software, no co-authored material. The
relation is restated from first principles and everything below is new.

## Step 1 — prior art

`novelty/search_prior_art.py`, PubMed E-utilities and Europe PMC, run 2026-09-06. Queries,
counts and records are stored in `novelty/results.json`; the script prints them with
`--report`. Each query was written down with what a hit would mean **before** it was run.

| query | PubMed | Europe PMC | what the hits were |
|---|---|---|---|
| A. image-based cardiac gating in CT | 10 | 28 | The kymogram line: Kachelriess (Med Phys 2002), Eur Radiol 2008, Acad Radiol 2005, plus intrinsic gating for small-animal CT (Circ Cardiovasc Imaging 2008). **All on cardiac or micro-CT protocols. The line stops around 2009.** |
| B. cardiac timing from a non-gated CT | 55 | 194 | Non-gated CT work is entirely structural — thrombus, calcium, aortic root, incidental infarct, epicardial fat. Data-driven gating appears only in PET/SPECT/MRI. **Nothing recovers cardiac timing from a non-gated CT.** |
| C. the sampling bound itself | 1 | 1 | One 2004 *Rofo* paper on z-flying-focal-spot performance. Not a feasibility condition for cardiac timing. **No hit.** |
| D. opportunistic cardiac assessment on chest CT | 94 | 84 | Busy and growing, and entirely structural. CMS created HCPCS G0680 for algorithmic CAC/AVC from chest CT effective 2026-04-01, so the genre is funded and reimbursed. **No functional or temporal work.** |
| E. cardiac motion in non-gated CT | 12 | 21 | Motion **correction**: deep-learning artefact reduction on chest CT (2026), diffusion models for calcium motion, implicit-neural dynamic reconstruction (Phys Med Biol 2026). The field treats the motion as noise. |

Two things follow. The mechanism is not new — image-based cardiac gating is a real, if
dormant, line of work. **Its boundary is what is missing.** The kymogram succeeded on
cardiac protocols and was never carried to routine ones, and no paper records why. The
reason turns out to be computable, and that is the contribution.

The second is that the audience exists and is active: everyone in query E is trying to
remove cardiac motion from non-gated chest CT, several with generative models. A bound on
what a single non-gated pass can contain constrains all of them, because no reconstruction
recovers information the acquisition never wrote.

**Limitation.** Two databases, title/abstract fields, English. This does not replace a
search with controlled vocabulary and full-text; it is enough to justify continuing, not
enough to assert priority.

## Step 2 — the bound

`analysis/sampling_bound.py`. Two requirements, pulling against each other:

- **enough cycles to have a period at all** — `N = L / W >= N_min`, an upper limit on speed
- **enough slices to resolve each cycle** — `n = W / dz >= n_min`, a lower limit on speed

giving a window on the table speed:

```
n_min x dz / Th   <=   S   <=   L / (Th x N_min)
```

where `L` is the craniocaudal extent of the heart (120 mm assumed) and `dz` is the coarser
of the reconstruction interval and the single-row collimation — reconstructing finer than
a detector row interpolates, it does not create information about z.

**The budget identity.** `N x n = L / dz`, independent of pitch, rotation time and heart
rate. A protocol cannot acquire more cardiac timing by running faster or slower; it can
only divide a fixed budget between cycles observed and resolution within a cycle.

### Where real protocols fall, at 60 bpm

| protocol | S (mm/s) | cycles | slices/cycle | recoverable? |
|---|---:|---:|---:|---|
| 2003 4-row, row-pitch 6 (the original) | 6.0 | 20.0 | 12.0 | yes |
| 2003 4-row, row-pitch 3 (reported aliased) | 3.0 | 40.0 | 6.0 | no, aliased |
| 2026 routine chest, 64 x 0.6, pitch 1.0 | 76.8 | 1.56 | 76.8 | no, too fast |
| 2026 lung screening, pitch 1.2 | 92.2 | 1.30 | 92.2 | no, too fast |
| 2026 wide detector, 192 x 0.6, pitch 1.5 | 691 | 0.17 | 1152 | no, too fast |
| 2026 dual-source high pitch | 1475 | 0.08 | 2458 | no, too fast |
| cardiac CT, retrospective gating, pitch 0.2 | 27.4 | 4.38 | 45.7 | yes |

### Read as a condition on the heart, which is the interesting direction

A shorter cardiac cycle packs more cycles into the same scanned length, so the threshold is
a heart **rate**: `threshold = 60 x S x N_min / L`.

| protocol | recoverable heart rates |
|---|---|
| 2003 original | 9 – 90 bpm |
| 2026 routine chest, pitch 1.0 | **115 – 576 bpm** |
| 2026 lung screening | 138 – 691 bpm |
| 2026 wide detector | 1037 – 8640 bpm |
| cardiac CT, retrospective gating | 41 – 343 bpm |

The 2003 window and the modern routine window are **disjoint**. The technique did not stop
working; the window moved off the resting heart. And it moved onto the tachycardic one —
115 bpm is reachable, and is the state of a patient being scanned for pulmonary embolism,
sepsis or trauma, which is when a non-gated chest CT is being acquired anyway.

### Two independent checks

- The bound says a **retrospectively gated cardiac protocol is feasible**. That is exactly
  where kymogram gating was published and shown to work. The bound says yes where the
  literature succeeded and no where nobody tried, which is the behaviour it needs.
- The bound reproduces the 2003 observation that row-pitch 3 aliased while row-pitch 6 did
  not, as 6 versus 12 slices per cycle. **This is a consistency check and not evidence**:
  `n_min = 8` was chosen knowing that outcome.

### What the result depends on

The threshold rate is `60 x S x N_min / L`. It is proportional to `N_min` and does not
contain `n_min` at all, so the constant that was calibrated decides nothing, and the
constant that decides everything was not calibrated — it was assumed.

| `N_min` | threshold, routine chest | at rest (60–100 bpm) |
|---:|---:|---|
| 2.0 | 77 bpm | some resting patients qualify |
| 2.5 | 96 bpm | some resting patients qualify |
| 3.0 | 115 bpm | none qualify |
| 4.0 | 154 bpm | none qualify |

**The headline flips between 2.5 and 3.0 cycles.** `N_min = 3` is a Nyquist-plus-margin
assumption, not a measurement.

## What is established, and what is not

Established: the relation, the window in closed form, the budget identity, where current
protocols fall, and that no indexed paper states this condition.

**Not established:** `N_min`. How many cardiac cycles a real estimator needs, given image
noise, the detectability of the cardiac border against lung and mediastinum, and an
irregular rhythm. Until that is measured the boundary has a position but not a value, and
the paper cannot claim where it lies.

That is the whole of step 3, and the analysis has narrowed it to one number.

## Verification

- `python -m pytest analysis/test_sampling_bound.py -q` — 11 tests
- The tests were shown to fail on four injected defects (dropped pitch conversion,
  interpolation counted as information, swapped window edges, cycles counted against the
  scan length rather than the heart) before being trusted to pass.

## Constraints carried from the source material

- The 2003 directory `../NonECG-Paper` contains **patient names and hospital identifiers**
  in `YamamotoPaper.txt`. It is excluded here and must never enter this repository.
- That manuscript had fourteen co-authors and two companies. Its phantom data, patient
  data, figures and software are theirs as well. **Nothing from it is used.**
- The 2003 submission was not rejected for being wrong. Reviewer 2 called it "very
  original" and then wrote that ventricular function, against echocardiography, nuclear
  medicine and MRI, made it "unlikely to have a significant impact." That framing is not
  reused: this is a sampling result, not a cardiac-function method.
