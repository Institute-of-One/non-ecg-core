"""Build the Technology and Health Care submission for IORN-011.

    python paper/build_submission_thc.py

Writes into ``paper/build/``:

    THC_title_page.docx     title, author, affiliation, corresponding author, ORCID
    THC_manuscript.docx     abstract, keywords, text, acknowledgements, declarations,
                            references and figure legends
    THC_supplementary.docx  the supplementary material, with its own reference list
    figures_thc/Fig1.png .. the five body figures, uploaded separately

What this journal asks for that the previous one did not (read off its own
submission guidelines on 2026-11-05):

* a **structured** abstract of **200 words**, counted here after the markers
  are resolved, because the limit applies to what the editor reads;
* **4 to 7** keywords;
* the declarations **in the article** under the journal's own six
  sub-headings (``declarations_thc.md``);
* **Sage Vancouver** references: numbered with a full point, in order of first
  citation, cited as superscript numerals after the punctuation. The prose is
  written in author-year, which is the form the previous journal wanted and
  the form ``check_references.py`` validates; it is converted here, and a
  parenthesis that is not a citation is left alone.
* figures as separate files, so the body carries legends and no images.

Review is single-anonymized, so nothing is withheld.

The three references of the auxiliary experiment are cited only in the
supplementary material now that the section has moved there, so the
supplement carries its own numbered list rather than leaving three entries
uncited in the article's.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.shared import Inches, Pt, RGBColor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_submission as P      # noqa: E402  marker resolution and docx helpers
import check_references as C      # noqa: E402  the author-year form of each record

BUILD = HERE / "build"
MANIFEST = HERE / "frozen" / "manifest.json"
RESOLVED = HERE / "frozen" / "references_resolved.json"
# Not under `frozen/`: that directory holds what produces the numbers, and
# `presubmission_check.py` requires none of it to have moved since the release
# the manuscript names. This is a table of Index Medicus journal names for the
# reference list -- it formats a citation and computes nothing -- so keeping it
# there made the gate red for a reason that was not true.
ABBREVIATIONS = HERE / "journal_abbreviations.json"

ABSTRACT_WORDS = 200
KEYWORDS = (4, 7)
ABSTRACT_SECTIONS = ["BACKGROUND", "OBJECTIVE", "METHODS", "RESULTS", "CONCLUSIONS"]
DECLARATIONS = ["Ethical considerations", "Consent to participate",
                "Consent for publication", "Declaration of conflicting interest",
                "Funding statement", "Data availability"]

AUTHOR = "Shuji Yamamoto"
AFFILIATION = "Institute of One, LISIT Co., Ltd., Tokyo 150-0044, Japan"
EMAIL = "yamamoto@lisit.jp"
ORCID = "0000-0001-9211-1071"

BODY_FONT = "Times New Roman"
BODY_SIZE = Pt(11)

CITE_KEY = re.compile(r"\[\[cite:([a-z0-9_]+)\]\]")
# `\s*` and not ` ?`: the manuscript is hard-wrapped, so the space before a
# citation can be a line break, and leaving it produced "examination ;1".
PARENTHETICAL = re.compile(r"\s*\(([^()]{4,240})\)([.,;:])?")
SUP_OPEN, SUP_CLOSE = "⁠SUP:", "⁠"


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------


def tidy(entry: str) -> str:
    return re.sub(r" {2,}", " ", entry).strip()


def vancouver(record: dict, abbrev: dict) -> str:
    """Sage Vancouver: up to three authors, then et al.; Index Medicus journal.

    The entry is whitespace-normalised at the end: one corporate author is
    deposited with a double space inside its name and printed with it.
    """
    names = [("%s %s" % (a["family"], a.get("initials", ""))).strip()
             for a in record["authors"]]
    if not names:
        who = "Anon."
    elif len(names) > 3:
        who = ", ".join(names[:3]) + ", et al."
    elif len(names) == 1:
        who = names[0] + "."
    else:
        who = ", ".join(names[:-1]) + " and " + names[-1] + "."

    title = re.sub(r"\s+", " ", record["title"]).strip().rstrip(".")
    container = record.get("container", "")
    year = record["year"]

    if record.get("dataset"):
        return tidy("%s %s [dataset]. %s, https://doi.org/%s (%d, accessed 5 November 2026)."
                    % (who, title, container, record["doi"], year))
    if container in ("arXiv",) or record.get("type") == "posted-content":
        return tidy("%s %s. arXiv, https://doi.org/%s (%d, accessed 5 November 2026)."
                    % (who, title, record["doi"], year))

    short = abbrev.get(container, {}).get("abbreviation") or container
    volume = record.get("volume") or ""
    pages = (record.get("pages") or "").replace("-", "–")
    tail = "%s %d" % (short, year)
    if volume:
        tail += "; %s" % volume
    if pages:
        tail += ": %s" % pages
    return tidy("%s %s. %s." % (who, title, tail))


def load_records() -> tuple[list[dict], dict]:
    records = json.loads(RESOLVED.read_text(encoding="utf-8"))
    abbrev = json.loads(ABBREVIATIONS.read_text(encoding="utf-8"))
    missing = [r["container"] for r in records
               if not r.get("dataset") and r.get("type") == "journal-article"
               and r.get("container") not in abbrev]
    if missing:
        raise SystemExit("no Index Medicus abbreviation on record for: %s "
                         "-- resolve it from Europe PMC into %s"
                         % (sorted(set(missing)), ABBREVIATIONS.name))
    return records, abbrev


class Numbering:
    """Citation keys in order of first appearance."""

    def __init__(self, records: list[dict]) -> None:
        self.by_citation = {C.citation_string(r): r["key"] for r in records
                            if not r.get("dataset")}
        self.by_key = {r["key"]: r for r in records}
        self.order: list[str] = []

    def number(self, key: str) -> int:
        if key not in self.by_key:
            raise SystemExit("no reference with key %r" % key)
        if key not in self.order:
            self.order.append(key)
        return self.order.index(key) + 1

    def compress(self, nums: list[int]) -> str:
        nums = sorted(set(nums))
        parts, run = [], [nums[0]]
        for n in nums[1:]:
            if n == run[-1] + 1:
                run.append(n)
            else:
                parts.append(run)
                run = [n]
        parts.append(run)
        return ",".join("%d–%d" % (r[0], r[-1]) if len(r) > 2
                        else ",".join(map(str, r)) for r in parts)

    def convert(self, text: str) -> str:
        text = CITE_KEY.sub(lambda m: "%s%d%s" % (SUP_OPEN, self.number(m.group(1)),
                                                  SUP_CLOSE), text)

        def repl(m: re.Match) -> str:
            fragments = [f.strip() for f in m.group(1).split(",")]
            if not fragments or not all(f in self.by_citation for f in fragments):
                return m.group(0)
            nums = [self.number(self.by_citation[f]) for f in fragments]
            return "%s%s%s%s" % (m.group(2) or "", SUP_OPEN, self.compress(nums),
                                 SUP_CLOSE)

        return PARENTHETICAL.sub(repl, text)


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


def add_runs_sup(paragraph, text: str) -> None:
    """P.add_runs, with the marked citations set as superscripts."""
    for piece in re.split("(%s[^%s]*%s)" % (SUP_OPEN, SUP_CLOSE, SUP_CLOSE), text):
        if not piece:
            continue
        if piece.startswith(SUP_OPEN):
            run = paragraph.add_run(piece[len(SUP_OPEN):-len(SUP_CLOSE)])
            run.font.superscript = True
        else:
            P.add_runs(paragraph, piece)


def new_document() -> docx.Document:
    document = docx.Document()
    for section in document.sections:
        section.page_width, section.page_height = Inches(8.27), Inches(11.69)
        for margin in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(section, margin, Inches(1.0))
    normal = document.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = BODY_SIZE
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    normal.paragraph_format.space_after = Pt(6)
    return document


def write_blocks(document, markdown: str, *, keep_figures: bool = False) -> list[str]:
    """Render markdown; returns the figure captions it met, in order."""
    captions: list[str] = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        index += 1
        if not line.strip():
            continue

        image = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line.strip())
        if image:
            if not keep_figures:
                continue
            path = (HERE / image.group(2)).resolve()
            if not path.is_file():
                raise SystemExit("figure missing: %s" % path)
            document.add_picture(str(path), width=Inches(6.1))
            document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            document.paragraphs[-1].paragraph_format.keep_with_next = True
            continue

        if line.startswith("### ") or line.startswith("## "):
            level = 2 if line.startswith("### ") else 1
            heading = document.add_heading("", level=level)
            add_runs_sup(heading, line.split(" ", 1)[1].strip())
            for run in heading.runs:
                run.font.color.rgb = RGBColor(0, 0, 0)
            continue
        if line.startswith("# "):
            heading = document.add_heading(line[2:].strip(), level=0)
            for run in heading.runs:
                run.font.color.rgb = RGBColor(0, 0, 0)
            continue
        if line.strip() == "---":
            continue

        block = [line]
        while index < len(lines) and lines[index].strip() and not re.match(
                r"^(#{1,3} |!\[|> |\d+\. |---$)", lines[index]):
            block.append(lines[index].rstrip())
            index += 1
        text = " ".join(block).strip()

        if text.startswith("**Figure ") or text.startswith("**Figure "):
            captions.append(text)
            if not keep_figures:
                continue

        if text.startswith("> "):
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.35)
            add_runs_sup(paragraph, text[2:])
            for run in paragraph.runs:
                run.italic = True
            continue

        numbered = re.match(r"^(\d+)\. (.*)$", text)
        if numbered:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.35)
            paragraph.paragraph_format.first_line_indent = Inches(-0.35)
            paragraph.paragraph_format.space_after = Pt(4)
            add_runs_sup(paragraph, text)
            continue

        paragraph = document.add_paragraph()
        if text.startswith("**Figure "):
            fmt = paragraph.paragraph_format
            fmt.left_indent = Inches(0.3)
            fmt.right_indent = Inches(0.3)
            fmt.space_before = Pt(4)
            fmt.space_after = Pt(14)
            fmt.line_spacing_rule = WD_LINE_SPACING.SINGLE
            fmt.keep_together = True
            add_runs_sup(paragraph, text)
            for run in paragraph.runs:
                run.font.size = Pt(9.5)
            continue
        add_runs_sup(paragraph, text)
    return captions


def section_of(text: str, start: str, end: str | None) -> str:
    i = text.index(start)
    j = text.index(end) if end else len(text)
    return text[i:j]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=BUILD)
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records, abbrev = load_records()

    def source(name: str) -> str:
        """Read, drop the author's notes to themselves, resolve the markers.

        The manuscript carries five HTML comments, three of them paragraphs
        explaining a framing decision to whoever edits next. The first build
        here left them in and the opening of the Introduction read
        "<!-- The framing decision, made deliberately: ...". The previous
        journal's build strips them; this one did not, and nothing but
        looking at the first page would have shown it.
        """
        text = (HERE / name).read_text(encoding="utf-8")
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        return P.resolve_markers(text, manifest)

    body_md = source("manuscript.md")
    abstract_md = source("abstract_thc.md")
    decl_md = re.sub(r"<!--.*?-->", "",
                     (HERE / "declarations_thc.md").read_text(encoding="utf-8"), flags=re.S)
    supp_md = source("supplementary.md")

    title = " ".join(section_of(abstract_md, "## Title", "## Abstract")
                     .splitlines()[1:]).strip()
    abstract = section_of(abstract_md, "## Abstract", "## Keywords")
    abstract = abstract[len("## Abstract"):].strip()
    keywords = " ".join(section_of(abstract_md, "## Keywords", "## Notes")
                        [len("## Keywords"):].split())

    failures: list[str] = []
    words = len(abstract.replace("**", "").split())
    if words > ABSTRACT_WORDS:
        failures.append("the abstract is %d words; this journal asks for %d"
                        % (words, ABSTRACT_WORDS))
    for s in ABSTRACT_SECTIONS:
        if ("**%s:**" % s) not in abstract:
            failures.append("the abstract has no %s heading" % s)
    n_keywords = len([k for k in keywords.split(";") if k.strip()])
    if not KEYWORDS[0] <= n_keywords <= KEYWORDS[1]:
        failures.append("there are %d keywords; this journal asks for %d to %d"
                        % (n_keywords, *KEYWORDS))
    for heading in DECLARATIONS:
        if ("### " + heading) not in decl_md:
            failures.append("the declarations are missing %r" % heading)

    # The body alone: not its title block, which the title page carries and
    # which was printing a second time under the abstract; not its own
    # abstract, which this journal structures differently; not its
    # declarations, which this journal gives its own headings; and not its
    # reference list, which is rebuilt in citation order.
    text = body_md[body_md.index("## 1. Introduction"):body_md.index("## Declarations")]

    numbering = Numbering(records)
    body = numbering.convert(text)
    ack = numbering.convert(section_of(decl_md, "## Acknowledgements",
                                       "## Statements and Declarations"))
    declarations = numbering.convert(section_of(decl_md, "## Statements and Declarations",
                                                None))

    def black_heading(document, text: str, level: int):
        heading = document.add_heading(text, level=level)
        for run in heading.runs:
            run.font.color.rgb = RGBColor(0, 0, 0)
        return heading

    def reference_list(document, order, heading: str, prefix: str = "") -> None:
        black_heading(document, heading, 1)
        for i, key in enumerate(order.order, start=1):
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.35)
            paragraph.paragraph_format.first_line_indent = Inches(-0.35)
            paragraph.paragraph_format.space_after = Pt(4)
            P.add_runs(paragraph, "%s%d. %s"
                       % (prefix, i, vancouver(order.by_key[key], abbrev)))

    document = new_document()
    black_heading(document, title, 0)
    black_heading(document, "Abstract", 1)
    for block in [b for b in abstract.split("\n\n") if b.strip()]:
        add_runs_sup(document.add_paragraph(), " ".join(block.split()))
    black_heading(document, "Keywords", 1)
    document.add_paragraph(keywords)
    captions = write_blocks(document, body)
    write_blocks(document, ack)
    write_blocks(document, declarations)
    reference_list(document, numbering, "References")
    black_heading(document, "Figure legends", 1)
    for caption in captions:
        add_runs_sup(document.add_paragraph(), caption)

    args.out.mkdir(parents=True, exist_ok=True)
    document.save(args.out / "THC_manuscript.docx")

    # Title page.
    title_page = new_document()
    black_heading(title_page, title, 0)
    for line in (AUTHOR, AFFILIATION, "ORCID: %s" % ORCID,
                 "Corresponding author: %s, %s. E-mail: %s" % (AUTHOR, AFFILIATION, EMAIL)):
        title_page.add_paragraph(line)
    title_page.save(args.out / "THC_title_page.docx")

    # Supplement, with its own numbering and list.
    supp_numbering = Numbering(records)
    supp_document = new_document()
    supp_captions = write_blocks(supp_document,
                                 supp_numbering.convert(supp_md), keep_figures=True)
    if supp_numbering.order:
        reference_list(supp_document, supp_numbering, "Supplementary references", "S")
    supp_document.save(args.out / "THC_supplementary.docx")

    # Nothing may be left in author-year form, and every reference listed must
    # have been cited.
    leftover = [" ".join(m.group(0).split())
                for m in re.finditer(r"\([A-ZÀ-Ý][^()]{3,80}\s\d{4}[a-z]?\)", body)]
    if leftover:
        failures.append("citation(s) left in author-year form: %s" % leftover[:3])
    for name, document_text in (("manuscript", body + ack + declarations),
                                ("supplement", supp_md)):
        if "<!--" in document_text:
            failures.append("the %s still carries an author's note (<!-- ... -->), "
                            "which prints as body text" % name)
    # A citation that moved behind punctuation must not leave a space in front
    # of it: "population-scale examination ;1" reached the first proof.
    import docx as _docx
    built = _docx.Document(str(args.out / "THC_manuscript.docx"))
    loose = [" ".join(p.text[max(0, m.start() - 40):m.end() + 8].split())
             for p in built.paragraphs
             for m in re.finditer(r"\S\s+[.,;:](?!\d)", p.text)]
    if loose:
        failures.append("space before punctuation in %d place(s), e.g. %r"
                        % (len(loose), loose[0]))
    if len(captions) != 5:
        failures.append("the body carries %d figure legend(s); it should carry 5"
                        % len(captions))

    print("abstract: %d words (limit %d), %d keywords" % (words, ABSTRACT_WORDS,
                                                          n_keywords))
    print("body: %d references cited, %d figure legends"
          % (len(numbering.order), len(captions)))
    print("supplement: %d references cited, %d figures"
          % (len(supp_numbering.order), len(supp_captions)))
    print("wrote %s, the title page and the supplement" % (args.out / "THC_manuscript.docx"))

    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
