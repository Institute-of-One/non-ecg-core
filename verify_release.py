"""Does a clean copy of this repository still rebuild the paper's numbers and figures?

Run this before cutting a tag. A release is not verified by the tests passing in the
directory where it was written; it is verified by unpacking it somewhere empty, installing
only what the requirements name, and running the paths the manuscript depends on. An earlier
release in this programme passed every local test and could not be installed at all a year
later, because a dependency removed a function that was correct when it was written and
nothing had an upper bound.

What it checks: that `paper/collect_results.py` rebuilds every manifest metric to the same
value, and that `paper/figures.py` draws every figure that does not need an image, from a copy
that contains no figures, no virtual environment and no cached images, with only
`requirements-core.txt` installed.

Five figures cannot be drawn that way and are not expected to be. Figure 4 of the main text and
figures S1 and S3 to S5 of the supplementary material show a coronal reformat with the tracked
border on it, so they need the archive series themselves; S3 to S5 come from
analysis/audit_admitted_levels.py rather than from paper/figures.py. This repository does not
redistribute imaging data; the code fetches it from The Cancer Imaging Archive by series
identifier, which additionally requires `requirements.txt` and a network. The data-availability
statement in the manuscript says exactly this, and this script exists to keep the two in step.

    python verify_release.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
COPY = ("analysis", "paper", "results", "requirements.txt", "requirements-core.txt",
        "README.md", "LICENSE", "CITATION.cff", ".zenodo.json")
SKIP = {"__pycache__", "figures", "data_cache", "probe_cache", ".git", ".venv"}
#: Eight figures exist; two of them draw a coronal reformat and need the archive series, which
#: this repository does not redistribute. See the module docstring.
EXPECTED_FIGURES = 6


def run(command, cwd=None) -> subprocess.CompletedProcess:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        print((result.stdout or "")[-2000:])
        print((result.stderr or "")[-2000:])
    return result


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="verify-non-ecg-"))
    try:
        for name in COPY:
            source = REPO / name
            if not source.exists():
                print(f"FAIL: {name} is not in the repository")
                return 1
            if source.is_dir():
                shutil.copytree(source, work / name,
                                ignore=shutil.ignore_patterns(*SKIP))
            else:
                shutil.copy2(source, work / name)
        print(f"clean copy at {work}")

        if run([sys.executable, "-m", "venv", str(work / ".venv")]).returncode:
            print("FAIL: could not create a virtual environment")
            return 1
        scripts = "Scripts" if os.name == "nt" else "bin"
        python = work / ".venv" / scripts / ("python.exe" if os.name == "nt" else "python")

        print("installing requirements-core.txt")
        if run([str(python), "-m", "pip", "install", "-q", "--disable-pip-version-check",
                "-r", str(work / "requirements-core.txt")]).returncode:
            print("FAIL: the core requirements do not install")
            return 1

        print("rebuilding the manifest")
        if run([str(python), "paper/collect_results.py"], cwd=work).returncode:
            print("FAIL: the manifest cannot be rebuilt from a clean copy")
            return 1

        print("drawing the figures that do not need an image")
        if run([str(python), "paper/figures.py", "--without-images"], cwd=work).returncode:
            print("FAIL: the figures cannot be drawn from a clean copy")
            return 1

        here = json.loads((REPO / "paper/frozen/manifest.json").read_text(encoding="utf-8"))
        there = json.loads((work / "paper/frozen/manifest.json").read_text(encoding="utf-8"))
        differing = sorted(set(here["metrics"]) | set(there["metrics"]))
        differing = [k for k in differing
                     if here["metrics"].get(k) != there["metrics"].get(k)]
        figures = sorted(p.name for p in (work / "paper/figures").glob("*.png"))

        print()
        print(f"metrics rebuilt     : {len(there['metrics'])} "
              f"(repository holds {len(here['metrics'])})")
        print(f"metrics that differ : {differing if differing else 'none'}")
        print(f"figures drawn       : {len(figures)}")
        ok = not differing and len(figures) == EXPECTED_FIGURES
        print(f"\n{'PASS' if ok else 'FAIL'}: a clean copy with only requirements-core.txt "
              f"reproduces every number in the manuscript and every figure that does not "
              f"show an image")
        print("figure 4 and figures S1, S3-S5 additionally need the archive series, fetched "
              "by the code from TCIA; they are not reproducible offline and the manuscript "
              "says so")
        return 0 if ok else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
