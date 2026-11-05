"""The cover letter, as the PDF the submission system asks for.

Kept separate from the manuscript build because the letter is not part of the manuscript and
must not acquire its figures, headings or numbering. Same Word export settings, for the same
reason: background repagination off.

    python paper/build_cover_letter.py
    python paper/build_cover_letter.py --source paper/cover_letter_thc.md \
        --docx paper/build/THC_cover_letter.docx --pdf paper/build/THC_cover_letter.pdf

Word is driven through ``DispatchEx``, which starts its own instance. This script used to
write a PowerShell file that called ``New-Object -ComObject Word.Application``: that attaches
to the Word the author already has open and closes their document at the final ``Quit``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import docx
from docx.enum.text import WD_LINE_SPACING
from docx.shared import Inches, Pt

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "cover_letter.md"
BUILD = HERE / "build"
DOCX = BUILD / "cover_letter.docx"
PDF = BUILD / "PMB_cover_letter.pdf"
WD_FORMAT_PDF = 17


def export(docx_path: Path, pdf_path: Path) -> None:
    """Word's own export, in Word's own instance."""
    import win32com.client as com
    word = com.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        word.Options.Pagination = False      # or a figure-heavy export never terminates
    except Exception:                        # noqa: BLE001
        pass
    try:
        document = word.Documents.Open(str(docx_path), ReadOnly=True)
        try:
            document.SaveAs(str(pdf_path), FileFormat=WD_FORMAT_PDF)
        finally:
            document.Close(SaveChanges=False)
    finally:
        word.Quit()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--docx", type=Path, default=DOCX)
    ap.add_argument("--pdf", type=Path, default=PDF)
    ap.add_argument("--no-pdf", action="store_true",
                    help="write the .docx only; something else exports it")
    args = ap.parse_args()
    # Word resolves a relative path against its own working directory, not
    # this process's, and then reports the file as missing.
    source = args.source.resolve()
    docx_path, pdf_path = args.docx.resolve(), args.pdf.resolve()

    text = source.read_text(encoding="utf-8")
    document = docx.Document()
    for section in document.sections:
        section.page_width, section.page_height = Inches(8.27), Inches(11.69)
        for margin in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(section, margin, Inches(1.0))

    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    normal.paragraph_format.space_after = Pt(10)

    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        # The signature block is several short lines that must not be rejoined.
        if "\n" in block and max(len(line) for line in block.splitlines()) < 70:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(0)
            for position, line in enumerate(block.splitlines()):
                if position:
                    paragraph.add_run().add_break()
                paragraph.add_run(line.strip())
            continue
        document.add_paragraph(" ".join(block.split()))

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(docx_path)

    if args.no_pdf:
        print(f"  {docx_path.relative_to(HERE.parent)}  (no PDF requested)")
        return 0
    export(docx_path, pdf_path)
    if not pdf_path.is_file():
        raise SystemExit("cover letter PDF export failed")

    print(f"  {pdf_path.relative_to(HERE.parent)}  ({pdf_path.stat().st_size // 1024} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
