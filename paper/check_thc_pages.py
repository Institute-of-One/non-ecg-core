"""Export the Technology and Health Care documents and read the printed pages.

    python paper/check_thc_pages.py
    python paper/check_thc_pages.py --no-export

The .docx checks read paragraphs, and where a page breaks is invisible to
them: a heading can sit alone at the foot of a page and a figure caption can
be separated from its figure with every check green. This exports what the
editor will read and looks at the pages, then renders each one so that they
can be looked at, which is the step no script replaces.

Run it with the interpreter that has pywin32 and pypdfium2 (the system Python
on this machine), not with a virtual environment that carries only the
analysis stack. Word is driven through ``DispatchEx`` so that the author's own
Word is never touched, with background pagination off.

The same checks exist in ctc-core as manuscript/check_thc_pages.py; they are
written out here because each repository ships its own tooling and nothing is
shared between them.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
PAGES = BUILD / "pages_thc"

DOCS = ["THC_manuscript.docx", "THC_title_page.docx", "THC_cover_letter.docx",
        "THC_supplementary.docx"]
NEAR_BLANK = 40
WD_FORMAT_PDF = 17


def headings(path: Path) -> set[str]:
    import docx
    document = docx.Document(str(path))
    return {p.text.strip() for p in document.paragraphs
            if (p.style.name.startswith("Heading") or p.style.name == "Title")
            and p.text.strip()}


def export(paths: list[Path]) -> None:
    import win32com.client as com
    word = com.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        word.Options.Pagination = False
    except Exception:                                   # noqa: BLE001
        pass
    try:
        for path in paths:
            document = word.Documents.Open(str(path.resolve()), ReadOnly=True)
            try:
                document.SaveAs(str(path.with_suffix(".pdf").resolve()),
                                FileFormat=WD_FORMAT_PDF)
            finally:
                document.Close(SaveChanges=False)
            print("exported %s" % path.with_suffix(".pdf").name)
    finally:
        word.Quit()


def render(pdf: Path, out_dir: Path, dpi: int = 110) -> list[Path]:
    import pypdfium2 as pdfium
    out_dir.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(str(pdf))
    written = []
    for i in range(len(document)):
        image = document[i].render(scale=dpi / 72).to_pil()
        path = out_dir / ("%s_p%02d.png" % (pdf.stem, i + 1))
        image.save(path)
        written.append(path)
    return written


def check(pdf: Path, heads: set[str]) -> tuple[list[str], int]:
    from pypdf import PdfReader
    bad: list[str] = []
    pages = [(p.extract_text() or "") for p in PdfReader(str(pdf)).pages]
    for n, text in enumerate(pages, start=1):
        if len(re.sub(r"\s", "", text)) < NEAR_BLANK:
            bad.append("%s page %d is blank or nearly blank" % (pdf.name, n))
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            continue
        last = lines[-1]
        if re.fullmatch(r"\d{1,3}", last) and len(lines) > 1:
            last = lines[-2]
        if last in heads:
            bad.append("%s page %d ends with the heading %r; it is separated from "
                       "the text it introduces" % (pdf.name, n, last))
        # No rule here about captions. In these documents the caption sits
        # below its figure, and `pypdf` does not return the lines of a page
        # with a figure on it in reading order: the caption of a figure can be
        # extracted before the text above it. A first version flagged two
        # pages of the supplement as broken and a second flagged four, and
        # looking at the rendered pages showed every one of them correct. The
        # builder keeps a figure with its caption (`keep_with_next` on the
        # picture, `keep_together` on the caption); whether that held is read
        # off the page images, not guessed from the text order.
    return bad, len(pages)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--dpi", type=int, default=110)
    args = ap.parse_args()

    docs = [BUILD / name for name in DOCS]
    missing = [d.name for d in docs if not d.exists()]
    if missing:
        print("missing: %s -- run build_submission_thc.py first" % ", ".join(missing))
        return 1
    if not args.no_export:
        export(docs)

    bad: list[str] = []
    for doc in docs:
        pdf = doc.with_suffix(".pdf")
        if not pdf.exists():
            bad.append("%s was not exported" % pdf.name)
            continue
        found, pages = check(pdf, headings(doc))
        bad += found
        images = render(pdf, PAGES, args.dpi)
        print("%-28s %2d page(s), %d image(s)" % (pdf.name, pages, len(images)))

    for b in bad:
        print("FAIL %s" % b)
    if bad:
        return 1
    print("OK   no blank page and no orphaned heading. Now look at the images in "
          "%s: a figure beside its caption, and a table that reads." % PAGES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
