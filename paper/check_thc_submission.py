"""The pre-submission gate for Technology and Health Care.

    python paper/check_thc_submission.py
    python paper/check_thc_submission.py --selftest

``build_submission_thc.py`` enforces what the documents must contain: the
200-word structured abstract, the keyword count, the journal's six declaration
headings, the citation form, the absence of author notes. This reads what the
build does not:

* **the cover letter**, which is the first thing an editor reads and the thing
  most likely to carry a sentence from the last submission. A single author
  writes "I"; every figure the letter quotes must appear in the manuscript;
  the repository, the archive DOI and the version must be the ones the
  article's Data availability statement gives; and the two prior papers in
  this journal, which are the letter's argument for fit, must match the
  record read from Crossref rather than a recollection.
* **the account of the previous review**, which must name what was acted on
  and what was not. A letter that said only what had been fixed would be
  claiming more than the article does.

Every rule is proved against a planted defect by ``--selftest``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent

LETTER = "cover_letter_thc.md"
BODY = "manuscript.md"
DECLARATIONS = "declarations_thc.md"
ABSTRACT = "abstract_thc.md"
PRIOR = "prior_thc_papers.json"

REPO = "https://github.com/Institute-of-One/non-ecg-core"
RELEASE = "v0.1.1"
ARCHIVE = "10.5281/zenodo.23051189"
CONCEPT = "10.5281/zenodo.23034327"

# Figures the letter quotes from the study. Each must be in the manuscript.
LETTER_FIGURES = ["192", "Three of seventeen", "900 words"]

# The letter must say what the referee asked for and was not done.
NOT_DONE = ["motion phantom", "did not have access"]


def read(where: Path, name: str) -> str:
    return (where / name).read_text(encoding="utf-8")


def resolved_body(where: Path) -> str:
    """The manuscript as the editor reads it, with the markers filled in.

    The letter quotes numbers; the manuscript holds markers. Comparing the
    letter with the unresolved source said the manuscript does not contain
    192, which it does -- as `[[results:manifest.json:metrics.header_series]]`.
    """
    sys.path.insert(0, str(HERE))
    import build_submission as P
    manifest = json.loads((HERE / "frozen" / "manifest.json").read_text(encoding="utf-8"))
    return " ".join(P.resolve_markers(read(where, BODY), manifest).split())


def run(where: Path = HERE) -> list[str]:
    bad: list[str] = []
    letter = read(where, LETTER)
    flat_letter = " ".join(letter.split())
    body = resolved_body(where)
    decl = " ".join(read(where, DECLARATIONS).split())

    plural = sorted(set(w.lower() for w in re.findall(r"\b(we|our|ours|us)\b",
                                                      letter, flags=re.I)))
    if plural:
        bad.append("the cover letter uses the authorial plural %s; this is a "
                   "single-author paper" % plural)

    for figure in LETTER_FIGURES:
        if figure not in flat_letter:
            bad.append("the cover letter no longer quotes %r, which this gate "
                       "holds to the manuscript; update the gate with the letter"
                       % figure)
        elif figure == "192" and "192" not in body:
            bad.append("the cover letter quotes 192 series and the manuscript "
                       "does not")
        elif figure == "Three of seventeen" and "3" not in body:
            bad.append("the cover letter quotes the cohort outcome and the "
                       "manuscript does not")

    for phrase in NOT_DONE:
        if phrase not in flat_letter:
            bad.append("the cover letter does not say %r; a letter that reports "
                       "only what was fixed claims more than the article does"
                       % phrase)

    if REPO not in flat_letter:
        bad.append("the cover letter does not give the repository URL")
    if ARCHIVE not in flat_letter:
        bad.append("the cover letter does not cite the archive (%s)" % ARCHIVE)
    if RELEASE not in flat_letter:
        bad.append("the cover letter does not name the release (%s)" % RELEASE)
    for other in set(re.findall(r"10\.5281/zenodo\.\d+", flat_letter)) - {ARCHIVE}:
        bad.append("the cover letter cites a second archive DOI (%s)" % other)

    # The declarations must give the same release, and the concept DOI must be
    # labelled as what it is rather than offered as the article's archive.
    if ARCHIVE not in decl:
        bad.append("the Data availability statement does not cite %s" % ARCHIVE)
    if CONCEPT in decl and "most recent version" not in decl:
        bad.append("the concept DOI appears without saying that it resolves to "
                   "the most recent version, which is not the version this "
                   "article reports")

    prior = json.loads(read(where, PRIOR))
    for paper in prior["papers"]:
        ref = "%d;%s:%s" % (paper["year"], paper["volume"], paper["pages"])
        if ref not in flat_letter:
            bad.append("the cover letter does not cite the author's own %d paper "
                       "in this journal as %s, which is how %s records it"
                       % (paper["year"], ref, PRIOR))
    return bad


def selftest() -> int:
    ok = True
    baseline = run()
    print("baseline (%d finding(s))" % len(baseline))
    for b in baseline:
        print("   - %s" % b)

    def edit(name: str, old: str, new: str):
        # The sources are hard-wrapped, so a phrase to plant into may hold a
        # line break; matching it literally made one injection plant nothing.
        pattern = re.compile(r"\s+".join(re.escape(w) for w in old.split()))

        def do(where: Path) -> None:
            path = where / name
            text = path.read_text(encoding="utf-8")
            if len(pattern.findall(text)) != 1:
                raise SystemExit("injection target %r occurs %d time(s) in %s"
                                 % (old[:40], len(pattern.findall(text)), name))
            path.write_text(pattern.sub(new.replace("\\", "\\\\"), text, count=1),
                            encoding="utf-8")
        return do

    cases = [
        ("the letter writes the authorial plural",
         edit(LETTER, "I report this as what it is", "We report this as what it is"),
         "authorial plural"),
        ("the letter drops the motion phantom it does not have",
         edit(LETTER, "I did not have access to a scanner and a motion phantom",
              "A phantom study is planned"),
         "did not have access"),
        ("the letter is left on another archive",
         edit(LETTER, ARCHIVE, "10.5281/zenodo.23034327"),
         "does not cite the archive"),
        ("the letter drops the repository",
         edit(LETTER, REPO, "the project repository"),
         "repository URL"),
        ("the letter misstates the author's own prior paper",
         edit(LETTER, "2013;21:441-454", "2013;21:441-455"),
         "records it"),
        ("the declarations lose the archive",
         edit(DECLARATIONS, ARCHIVE, "10.5281/zenodo.1"),
         "Data availability statement"),
    ]

    names = [LETTER, BODY, DECLARATIONS, ABSTRACT, PRIOR]
    with tempfile.TemporaryDirectory() as tmp:
        for name, plant, expect in cases:
            work = Path(tmp) / re.sub(r"\W+", "_", name)[:40]
            work.mkdir()
            for f in names:
                shutil.copy(HERE / f, work / f)
            before = {f: (work / f).read_bytes() for f in names}
            plant(work)
            if before == {f: (work / f).read_bytes() for f in names}:
                print("  NO-OP    %s" % name)
                ok = False
                continue
            found = [f for f in run(work) if f not in baseline]
            hit = [f for f in found if expect in f]
            print("  %-8s %s" % ("DETECTED" if hit else "MISSED", name))
            if hit:
                print("           -> %s" % hit[0][:120])
            else:
                ok = False
                print("           expected %r, got %s"
                      % (expect, [f[:90] for f in found] or "nothing"))
    print("selftest %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    bad = run()
    for b in bad:
        print("FAIL %s" % b)
    if not bad:
        print("OK   the letter says what the article says, names what was not done, "
              "and cites the release the article reports")
    return int(bool(bad))


if __name__ == "__main__":
    raise SystemExit(main())
