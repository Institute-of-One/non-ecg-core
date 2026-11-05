# IORN-011 -- Statements and Declarations for Technology and Health Care

The journal requires this section **in the article**, at the end, with each of
its own sub-headings present even where the answer is "Not applicable" (read
off the journal's submission guidelines on 2026-11-05). The six headings below
are the journal's, in its order and with its wording.

The facts are those of the manuscript's own Declarations section, rearranged
under these headings. Two statements that belonged to the previous submission
are not carried over: the note of prior contact with that journal's editorial
office, which would be false here, and the author-and-affiliation block, which
this journal takes on the title page. The disclosure of generative AI moves to
the Acknowledgements, where ICMJE places it and where Sage's ethics resources
point.

Review is single-anonymized, so the repository, the archive and the author's
company are named.

## Acknowledgements

The research question, the physical argument of section 2, the study design
and the decision rules recorded in the repository are the author's and predate
the assistance described here. Generative AI (Claude, Anthropic) was used as a
tool in preparing this work: to write and test analysis code, to carry out the
survey of the public archive reported in section 5.4, to produce the figures
from the frozen result files, and to draft manuscript text from results that
already existed. No AI system contributed a research idea, chose a decision
rule, or determined a result. Every number in this paper is resolved at build
time from a result file produced by code in the public repository, every
reference is resolved from its DOI rather than written out, and the author has
checked the manuscript against those files and takes full responsibility for
its content, including the parts drafted with assistance.

## Statements and Declarations

### Ethical considerations

This study used only publicly available, de-identified imaging distributed by
The Cancer Imaging Archive under Creative Commons licences, and generated no
new patient data. Ethical approval was therefore not required and none was
sought: secondary analysis of de-identified public data does not constitute
human subjects research. Approval for the original acquisitions rests with the
contributing institutions and is recorded by the archive. Patient identifiers
and series instance identifiers appearing in the released results are the
archive's own de-identified ones.

### Consent to participate

Not applicable. No participant was recruited or contacted for this study, which
analysed images already published in de-identified form.

### Consent for publication

Not applicable. The article contains no identifiable individual data.

### Declaration of conflicting interest

The author declares the following potential conflict of interest with respect
to the research, authorship and publication of this article: the author is the
representative of LISIT Co., Ltd., a provider of medical imaging analysis
services, and this work was carried out within that company. The company
received no funding for the study, played no part in its design, analysis or
reporting, and markets no product based on the method examined here. The author
declares no competing interest beyond that affiliation.

### Funding statement

This work received no external funding. It was carried out within LISIT Co.,
Ltd., using the author's own company's equipment as support in kind.

### Data availability

All analysis code, the frozen decision rules and every result file from which
the figures and numbers in this paper are computed are available at
https://github.com/Institute-of-One/non-ecg-core, at the tagged release v0.1.1,
which accompanies this manuscript, and archived at Zenodo,
https://doi.org/10.5281/zenodo.23051189; the concept identifier
10.5281/zenodo.23034327 resolves to the most recent version. A clean copy of
that release, unpacked into an empty directory and installed from
`requirements-core.txt` alone, rebuilds every number in this paper to the same
value and draws every figure that does not show an image; `verify_release.py`,
in the release, is the script that checks it. Five figures do show one -- figure
4 in the main text and figures S1 and S4 to S6 in the supplementary material,
all of them coronal reformats -- and those need the archive series themselves.
No imaging data is redistributed here: the code retrieves it from The Cancer
Imaging Archive by series identifier, which requires the full
`requirements.txt` and a network connection. The collections from which series
were taken are cited as data: Anti-PD-1 Immunotherapy Lung [[cite:tcia_antipd1lung]],
Stony Brook University COVID-19 Positive Cases [[cite:tcia_covidnysbu]], CPTAC
Lung Adenocarcinoma [[cite:tcia_cptacluad]], A Large-Scale CT and PET/CT Dataset
for Lung Cancer Diagnosis [[cite:tcia_lungpetctdx]], the RIDER coffee-break lung
CT collection [[cite:tcia_riderlungct]] and VAREPOP-APOLLO
[[cite:tcia_varepopapollo]].
