# Supplementary material

Cardiac period estimation from non-gated helical CT: sampling criteria and exploratory
evaluation

Shuji Yamamoto, Institute of One, LISIT Co., Ltd., Tokyo 150-0044, Japan

This material records a run that is referred to in section 5.4 of the main text and is not
used in any estimate there. It is included because the protocol was fixed before the data
were fetched and the result should be visible whatever it turned out to be, and because the
way it failed is the reason the main text now reports where the tracked border lies.

## S1 The session, and the protocol fixed before it

A survey of 156 collections of The
Cancer Imaging Archive found
1 session holding both a
recorded heart rate and a free-running helical series of the chest: collection
VAREPOP-APOLLO, patient AP-26JK, study described as a cardiac CTA. A gated acquisition in
that session records 75.0 bpm, with a
minimum of 72.0 and a maximum of
78.0 over its own duration, written
into the free text of `ScanOptions (0018,0022)` rather than into `HeartRate (0018,1088)`,
which is empty. A helical series covering
630 mm at
208.7 mm/s, lasting
3.02 s, begins ten seconds later.

Before the images were downloaded, an interval for agreement was fixed at five per cent of
the recorded rate, 71.25 to
78.75 bpm, in
`analysis/tcia_search/validation_protocol.md`. Five per cent is the tolerance under which
*N*min was measured; the range the scanner itself recorded is narrower, at four per cent of
the mean. The unmodified pipeline was then run.

## S2 What the run returned, and why it is not used

The pipeline returned 67.4 bpm, which is
-10.2 per cent from the recorded rate and
outside the interval. The frozen criterion rejected the series, on a leave-one-out spread of
28.1 bpm.

Neither figure is evidence about cardiac timing, because the extraction did not return the
intended anatomical border (figure S1). The tracked position lies at
0.9 per cent of the image width, where
a mediastinum in the cohort lies between
41 and
48 per cent, and at one coronal level
it is constant to numerical precision across the whole scan. The acquisition runs from the
chin to the pelvis with the arms at the sides; the method takes the left edge of the
soft-tissue run crossing the midline of a coronal row, which is the mediastinal border only
where a lung breaks that run.

![Figure S1](figures/figS1_failed_extraction.png)

**Figure S1.** The coronal reformat of the series under test, at its own aspect, with the
tracked border drawn on it. Compare figure 4 of the main text, where the same code follows
the mediastinum between the two lungs.

![Figure S2](figures/figS2_reference_objective.png)

**Figure S2.** The objective of the joint fit across the physiological band for that series,
normalised to its minimum, with the recorded rate and the interval fixed in advance marked.
The recorded rate is not a local minimum, and the whole band lies within a fifth of the best
fit. Since the trace is not of the intended structure, this says nothing about whether a
cardiac period could have been recovered from a scan of this geometry; it is shown because
the objective looked no different from those of section 5.3 until the image was drawn.

## S3 What followed

`analysis/check_border_position.py`, which measures where the tracked border lies in every
cached series, was written after this run and did not exist while the cohort was analysed.
Applied to the cohort it finds
2 of
17 series within
10 per cent of the image
edge, and 2 more closer to the edge
than to the middle. All were rejected by the frozen criterion, and the
3 admitted series lie at
41 to
43 per cent.

## S4 The learned estimator of section 6, in full

Each trace has the same quartic baseline removed as every other estimator in this paper, is
divided by its own standard deviation, and is resampled to 128 points,
so the model sees one input shape and no absolute scale. The target is the period as a fraction
of the trace length, that is the reciprocal of the cycles written; it is dimensionless, and the
standard deviations reported in section 6 are in those units.

The model is a multilayer perceptron with three hidden layers of
256 units and rectified linear activations, ending in two linear heads
for the mean and the log variance. It is trained by minimising the Gaussian negative
log-likelihood with Adam for 40 epochs at a batch size of
256 on 60000 simulated traces. Accuracy is scored on
2000 independent traces at each of nine cycle counts, within the
5 per cent tolerance used in section 3. The learning rate and
every remaining setting are in `analysis/learned_estimator.py`.

Two models were trained under this identical recipe, differing only in the range of cycle
counts their traces spanned: 2.5 to 8.0 cycles for
the one trained at or above the bound, and 0.5 to
8.0 for the one trained across it.

## S5 The admitted series, level by level

Every usable coronal level of each series the frozen criterion admitted, drawn as a reformat at
its own aspect with the tracked border on it. These are the images behind section 5.5. Each panel
gives the level's position across the image, the excursion of its border, the share of slices for
which the tracker returned nothing, and, where it occurs, the longest run of identical values.

![Figure S3](figures/audit_admitted_1.png)

**Figure S3.** Admitted series 1, five usable levels.

![Figure S4](figures/audit_admitted_2.png)

**Figure S4.** Admitted series 2, five usable levels.

![Figure S5](figures/audit_admitted_3.png)

**Figure S5.** Admitted series 3, six usable levels. The tracked border continues past both ends
of the lung, where the image is soft tissue on both sides of it; that is the series whose cycles
fall from 2.77 to 1.68 when counted over
the stretch where the border is at a lung interface.
