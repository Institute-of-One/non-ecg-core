Dear Editors,

I am submitting the enclosed manuscript, "How much of a heartbeat a non-gated CT records: a
header-computable sampling bound, and what a learned estimator does beyond it", for
consideration as a Paper in Physics in Medicine and Biology.

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
every collection of The Cancer Imaging Archive for a session that records a heart rate
alongside a free-running helical chest series. Exactly one exists. Running the unmodified,
previously frozen pipeline on it, under an acceptance interval fixed in the public repository
before the images were downloaded, returned a rate ten per cent away from the recorded one on
a scan that wrote half again the required number of cycles.

Diagnosing that case changed the paper. The objective the fit minimises is nearly flat, the
recorded period is not a local minimum of it, and across the cohort the three series the
frozen criterion admitted have minima no deeper than those it rejected, with their coronal
levels individually preferring rates spanning some fifty beats per minute. The admissions are
therefore not recoveries; they are a flat objective being read as stability. This is reported
as a new section 5.3, and the case with a known rate as section 5.4. Both are post-hoc, both
were added in response to the Board member's comment, and both are declared as such in the
manuscript.

The cohort result reported in section 5.1 is unchanged and remains the one produced by the
criterion frozen before the data were fitted.

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
