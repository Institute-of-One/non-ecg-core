# Cover letter -- Technology and Health Care

Shuji Yamamoto
Institute of One, LISIT Co., Ltd., Tokyo 150-0044, Japan
yamamoto@lisit.jp | ORCID 0000-0001-9211-1071

6 November 2026

Dear Professor Li,

Please consider the enclosed manuscript, "Cardiac period estimation from
non-gated helical CT: sampling criteria and exploratory evaluation", as an
Original Research Article in Technology and Health Care.

Why this journal. The question is what an acquisition's own geometry decides
about a measurement made from it, and the answer is computed from DICOM
headers. That is the kind of work I have published in this journal before: a
DICOM image-based program for estimating patient exposure dose in CT
(2007;15:147-156) and a DICOM image-based CT low-dose simulator
(2013;21:441-454). This article asks the same sort of question of timing
rather than dose.

What it reports. A constant table speed makes the axial coordinate of a
helical scan a nominal time axis, so cardiac motion writes a spatial period
into the undulation of the mediastinal border. Two requirements follow, and
the cycles written and the samples per cycle multiply to a fixed budget set by
the scan length and the slice spacing: table speed divides that budget, it
does not enlarge it. The requirements are then evaluated against the headers
of 192 real series, which says what fraction of ordinary chest protocols could
support the measurement at all, before any image is opened. That is the part a
reader can act on: it is a protocol check, computable in advance.

What it reports as a negative result. The image evaluation did not recover a
period. Three of seventeen series met a self-consistency criterion that was
frozen before the data were fitted, and the article shows that those three are
not better than the fourteen it rejected: their cost minima are no deeper, and
their levels individually prefer rates tens of beats apart. An audit added
during revision showed that for part of every admitted series the tracked
border was not the structure intended. I report this as what it is. The
conclusion the evidence supports is about the criterion, not about the
measurement: self-consistency alone does not establish that a period was
found, and a fit needs the depth of its minimum and a check on what was
fitted. For a reader of this journal that has a practical form, and the
article now ends on it: a cardiac period or phase offered from a routine
non-gated chest CT should not be carried into clinical use on the strength of
a stable fit, and the two checks that would justify one are available -- the
sampling requirement, from the header before any image is opened, and the
depth of the minimum together with the reformat the trace was taken from.

What would settle it, and what this study does not do. Scans of a moving
phantom driven at known periods, across a range of table speeds and pitches,
would score recovery against truth in real reconstructed images and separate
the acquisition and extraction causes from each other. I did not have access
to a scanner and a motion phantom, and this work does not include such a
study; the Limitations say so in those terms, and say what a digital phantom
carried through helical forward projection would and would not reach. No claim
is made that no method could recover the period.

Previous consideration. This manuscript was reviewed by Physics in Medicine
and Biology and was not accepted. The referee's points were that the sampling
identity follows from the definitions, that the minimum-cycle requirement
comes from one-dimensional simulation, that the image evaluation does not
demonstrate successful estimation and would need a motion phantom, that the
uncertainty-estimation experiment was only loosely related, and that the
manuscript was too long. I have acted on the two I can act on without new
data: the auxiliary uncertainty experiment and its figure have moved to the
supplementary material, which shortens the article by about 900 words, and the
body is in the first person singular throughout, since there is one author.
The first three points stand as the referee put them, and the article does not
claim otherwise. I submit it because what it establishes -- a protocol check
computable from headers, and a demonstration that a self-consistent fit is not
a correct one -- is useful to a reader deciding whether to attempt this
measurement, and because both parts are fully reproducible from the released
code.

Reproducibility. Every number and figure is resolved at build time from result
files produced by code in a public repository,
https://github.com/Institute-of-One/non-ecg-core, at the tagged release
v0.1.1, archived at https://doi.org/10.5281/zenodo.23051189. A clean copy of
that release installed from its own requirements rebuilds every number in the
article and draws every figure that does not need an archive image;
verify_release.py, in the release, is the script that checks it.

Journal policies.

- The manuscript is original, is not under consideration elsewhere, and has
  not been published. I am the sole author and have approved it for
  submission. No preprint has been posted and none will be while it is under
  consideration.
- No EQUATOR Network reporting guideline applies: this is a computational
  study on public images, with no participants recruited, no clinical outcome
  and no diagnostic accuracy claim against a clinical reference standard. I
  will supply any checklist the editorial office considers applicable.
- Ethics: the study used only publicly available, de-identified imaging from
  The Cancer Imaging Archive and generated no new patient data, so ethical
  approval was not required and none was sought. This is stated under Ethical
  considerations in the article.
- Competing interest: I am the representative of LISIT Co., Ltd., within which
  the work was carried out. The company received no funding for the study and
  markets no product based on the method examined here. This is declared in
  the article.
- Funding: none.
- Use of generative AI is disclosed in the Acknowledgements: it was used under
  my direction to write and test analysis code, to run the archive survey, to
  draw the figures from frozen result files and to draft text from results
  that already existed. No AI system contributed a research idea, chose a
  decision rule or determined a result, and I am accountable for the content.

Review at this journal is single-anonymized, so the manuscript names the
repository, the archive and my affiliation, and no blinded copy is enclosed.

Yours sincerely,

Shuji Yamamoto
