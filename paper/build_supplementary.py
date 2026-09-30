"""Build the supplementary PDF, with the same machinery and the same marker resolution.

One PDF, not an archive: a supplementary zip was rejected twice by this publisher's system on
an earlier submission from this group, and the error blocked the whole batch.

    python paper/build_supplementary.py
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import build_submission as main_build

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "supplementary.md"
BUILD = HERE / "build"
DOCX = BUILD / "supplementary.docx"
PDF = BUILD / "PMB_supplementary.pdf"
RESOLVED = BUILD / "supplementary_resolved.md"
#: S1 and S2 (the reference case) plus S3-S5, one per admitted series, from the anatomical
#: audit of section 5.5.
EXPECTED_FIGURES = 5


def main() -> int:
    manifest = json.loads((HERE / "frozen" / "manifest.json").read_text(encoding="utf-8"))
    text = re.sub(r"<!--.*?-->", "", SOURCE.read_text(encoding="utf-8"), flags=re.S)
    text = main_build.resolve_markers(text, manifest)
    BUILD.mkdir(parents=True, exist_ok=True)
    RESOLVED.write_text(text, encoding="utf-8")

    main_build.build_docx(text, destination=DOCX, expected_figures=EXPECTED_FIGURES)

    script = BUILD / "export_supplementary.ps1"
    script.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        "$word = New-Object -ComObject Word.Application\n"
        "$word.Visible = $false\n"
        "$word.DisplayAlerts = 0\n"
        "$word.Options.Pagination = $false\n"
        f"$document = $word.Documents.Open('{DOCX}', $false, $true)\n"
        f"$document.ExportAsFixedFormat('{PDF}', 17)\n"
        "$document.Close(0)\n"
        "$word.Quit()\n",
        encoding="utf-8")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if result.returncode or not PDF.is_file():
        print(result.stdout[-1200:])
        print(result.stderr[-1200:])
        raise SystemExit("supplementary PDF export failed")
    print(f"  {PDF.relative_to(HERE.parent)}  ({PDF.stat().st_size // 1024} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
