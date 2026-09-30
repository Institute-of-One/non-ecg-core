"""Generate the submission kit from the built documents, so its numbers cannot go stale.

Why this exists. The kit is what gets typed into the portal, and three times in this programme a
number in it was wrong: a word count carried over from a previous build, a figure count that said
two after a revision made it five, and a novelty statement over the 100-word limit because the
count was estimated rather than measured. None of those is a hard problem; all of them come from
the same cause, which is that the kit was a document someone edited.

It is now a generated file. The prose lives in submission_kit.template.md, every count is
measured here from paper/build/, and the script refuses to write a kit that breaks a stated
limit. Run it after any build:

    python paper/build_submission.py && python paper/make_submission_kit.py

The fields themselves, and which of them the portal gets wrong, are in the template and in
D:/DevGit/IoO/docs/IoO_Submission_Runbook.md section 8.4. This script does not know about the
portal; it knows about the documents.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BUILD = HERE / "build"
TEMPLATE = HERE / "submission_kit.template.md"
KIT = HERE / "submission_kit.md"

#: The journal's own limits. A kit that breaks one is not written at all.
MAX_BODY_WORDS = 10_000
MAX_ABSTRACT_WORDS = 300
MAX_FIGURES = 12
MAX_NOVELTY_WORDS = 100

WORD = re.compile(r"[A-Za-z0-9'\u2013\u2010-]+")


def words(text: str) -> int:
    return len(WORD.findall(text))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True).stdout.strip()


def measure() -> dict[str, object]:
    """Everything the portal asks for that can be read off the documents."""
    resolved = (BUILD / "manuscript_resolved.md").read_text(encoding="utf-8")
    supplementary = (BUILD / "supplementary_resolved.md").read_text(encoding="utf-8")

    abstract = resolved.split("## Abstract")[1].split("---")[0]
    body = resolved.split("---", 1)[1].split("## References")[0]
    captions = "\n".join(re.findall(r"\*\*Figure \d+\.\*\*[^\n]*(?:\n(?!\n)[^\n]*)*", body))

    with_captions = words(body)
    novelty = TEMPLATE.read_text(encoding="utf-8").split("## Novelty and significance")[1]
    novelty = novelty.split("##")[0].strip()

    tag = next((line for line in git("tag", "--list").splitlines()
                if line in resolved), "")
    return {
        "date": date.today().isoformat(),
        "body_words": with_captions - words(captions),
        "body_words_with_captions": with_captions,
        "abstract_words": words(abstract),
        "main_figures": len(re.findall(r"\*\*Figure \d+\.\*\*", body)),
        "supplementary_figures": len(re.findall(r"\*\*Figure S\d+\.\*\*", supplementary)),
        "main_pages": fitz.open(BUILD / "PMB_manuscript.pdf").page_count,
        "supplementary_pages": fitz.open(BUILD / "PMB_supplementary.pdf").page_count,
        "cover_letter_pages": fitz.open(BUILD / "PMB_cover_letter.pdf").page_count,
        "novelty_words": words(novelty),
        "tag": tag or "(the manuscript names no release)",
        "commit": git("rev-parse", "--short", "HEAD"),
    }


def main() -> int:
    if not TEMPLATE.is_file():
        raise SystemExit(f"no template at {TEMPLATE}")
    values = measure()

    limits = [
        ("body words", values["body_words_with_captions"], MAX_BODY_WORDS),
        ("abstract words", values["abstract_words"], MAX_ABSTRACT_WORDS),
        ("figures", values["main_figures"], MAX_FIGURES),
        ("novelty statement words", values["novelty_words"], MAX_NOVELTY_WORDS),
    ]
    broken = [f"{name}: {value} over {limit}" for name, value, limit in limits if value > limit]
    for name, value, limit in limits:
        print(f"  {'FAIL' if value > limit else 'ok  '}  {name:24s} {value:6d}  (limit {limit})")
    if broken:
        raise SystemExit("\nnot written: " + "; ".join(broken))

    text = TEMPLATE.read_text(encoding="utf-8")
    unknown = {m for m in re.findall(r"\{\{(\w+)\}\}", text)} - set(values)
    if unknown:
        raise SystemExit(f"the template uses markers with no measurement: {sorted(unknown)}")
    for key, value in values.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))

    KIT.write_text(text, encoding="utf-8")
    print(f"\nwritten: {KIT}")
    print("Every number above was measured from paper/build/. Do not edit the kit; edit the "
          "template and run this again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
