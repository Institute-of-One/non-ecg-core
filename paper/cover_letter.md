Dear Editors,

I am submitting the enclosed manuscript, "Cardiac period estimation from non-gated helical
CT: sampling criteria and exploratory evaluation", for consideration as a Paper in Physics
in Medicine and Biology.

A coronal reformat of a non-gated helical chest CT shows the mediastinal border as an
undulating line, normally read as a motion artefact. Because the table advances at a constant
speed, that line is also a record of the cardiac cycle, and if its timing could be read out an
examination already acquired could be sorted by cardiac phase without an electrocardiogram.
Every use of that begins with the cardiac period, and the paper concerns only that first step.
It states the two sampling requirements recovery must satisfy, shows that their product is
fixed by the structure extent and the reconstruction interval, measures the cycles one
estimator needs in simulation, evaluates the requirements on 192 real series from their
headers, and tests recovery on 17 image series under a criterion frozen in advance. The image
evaluation is exploratory and the manuscript says so: no public acquisition pairs a
reconstructed helical chest series with a recorded rate, so a self-consistent estimate cannot
be shown to be a correct one. Phase identification, phase-resolved reconstruction and
ventricular volumetry are not examined.

I contacted the editorial office before this submission to ask whether the work was suited to
a Paper rather than a Note. A Board member kindly reviewed the enquiry and confirmed that it
could be submitted as a Paper, and the office asked that I mention the prior contact here.

The Board member also raised a substantive concern, which I have addressed as far as the
available data allow, and I would like to be explicit about what I was and was not able to
do. The concern was that the recovery criterion had been derived and tested on simulated
motion and then applied to real acquisition parameters, without ever testing recovery from
the corresponding images, and that the low recovery rate in the image cohort could therefore
not be attributed to the acquisition, the extraction method or genuine cardiac variation.

I do not have access to a CT scanner or a motion phantom, so the phantom study the Board
member suggested is not part of this work, and section 8 says so plainly. Instead I searched
all 156 collections of The Cancer Imaging Archive for a session that records a heart rate
alongside a free-running helical chest series. Exactly one exists, and it could not be used.
The acceptance interval was fixed in the public repository before the images were downloaded,
but a check I wrote afterwards shows that the extraction did not return the anatomical border
the method is defined on: its tracked position sits within one per cent of the image edge,
and at one coronal level it is constant to numerical precision across the whole scan. No
comparison with the recorded rate is therefore available, and the run enters no estimate of
accuracy. It is reported as section 5.4 with the protocol that preceded it.

Looking for that failure changed the paper three times. Measured across the cohort, four
further series have extractions that are suspect on the same test, all of them already rejected
by the frozen criterion. Separately, the objective the fit minimises turned out to be nearly
flat: the three series the criterion admitted sit at depths of 1.106 to 1.142 against a rejected
median of 1.072, and their coronal levels — five, five and six of them — fitted independently,
prefer rates differing by 44 to 59 beats per minute within a series. That is section 5.3.

The third change came from doing what the position check does not do. I drew all sixteen usable
coronal levels of the three admitted series as reformats with the tracked border on them and
looked at every one. None is at the skin, so the failure of the reference case does not recur.
But 13 per cent of the tracked points sit at no lung–soft-tissue interface at all: beyond the
lung base and past the apex the tracker still returns a border where the image is soft tissue on
both sides. Re-counting cycles over the stretch of each series where the border is genuine, one
of the three admissions writes 1.68 cycles rather than the 2.77 the frozen criterion recorded,
so it does not meet this paper's own cycle-count condition where the measurement is valid. That
is section 5.5, with the images in the supplementary material. I have reported it rather than
adding a caveat, and the frozen cohort outcome of section 5.1 is unchanged by it.

These three analyses are post-hoc, all were prompted by the Board member's comment, and all are
declared as such in the manuscript.

The cohort result reported in section 5.1 is unchanged and remains the one produced by the
criterion frozen before the data were fitted. I should be plain that the Board member's
concern is not resolved: there is no public acquisition on which recovery from images can be
checked against a known rate, and the manuscript now says so rather than working around it.
What it claims has been narrowed to what the evidence carries. The sampling bound is a
consequence of the definitions; the constant in it is empirical and estimator-dependent; the
header survey states what protocols could record rather than what they did; and the image
cohort demonstrates that a self-consistency criterion can certify a fit to a flat objective.

All analysis code, the frozen decision rules and every result file behind the figures and
numbers are public at https://github.com/Institute-of-One/non-ecg-core, at the tagged release
this manuscript accompanies. An archived copy with a DOI is being deposited and I will
provide the identifier at revision. No imaging data is redistributed; the analysis retrieves
it from the archive by series identifier.

The manuscript has not been published elsewhere and is not under consideration by another
journal. I am the sole author. I confirm that the work includes author-identifying
information and that I accept it will therefore be handled as a single-anonymous submission.

Thank you for considering it.

Yours sincerely,

Shuji Yamamoto
Institute of One, LISIT Co., Ltd., Tokyo 150-0044, Japan
ORCID 0000-0001-9211-1071
yamamoto@lisit.jp
