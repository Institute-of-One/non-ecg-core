"""Is this repository in a state where a tag can be cut, and does it agree with itself?

The reproducibility gate is verify_release.py. This is the other half: the metadata a release
carries, and the agreements between files that nothing else checks. Each rule here exists
because breaking it has cost this programme something.

  - a top-level `doi` in .zenodo.json stops Zenodo minting a version DOI of its own
  - a version in .zenodo.json that disagrees with CITATION.cff makes the archive and the
    citation file describe different things
  - `date-released` that is not the day the tag is cut is a small untruth no one notices
  - a result file the manifest loads but git does not track is absent from the release, and
    the manuscript then cites numbers the archive cannot reproduce
  - an unpushed commit at tag time means the archived tree is not the reviewed one
  - once a release exists, CITATION.cff must carry the concept DOI, not the placeholder

    python check_release_metadata.py            # before the first tag
    python check_release_metadata.py --released  # after a release exists: requires the DOI
"""

from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
AFFILIATION = "Institute of One, LISIT Co., Ltd., Tokyo 150-0044, Japan"
ORCID = "0000-0001-9211-1071"


def git(*arguments) -> str:
    return subprocess.run(["git", *arguments], cwd=REPO, capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def main() -> int:
    released = "--released" in sys.argv
    failures: list[str] = []

    def check(label: str, passed: bool, detail: str = "") -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {label}{'  | ' + detail if detail else ''}")
        if not passed:
            failures.append(label)

    zenodo = json.loads((REPO / ".zenodo.json").read_text(encoding="utf-8"))
    citation = (REPO / "CITATION.cff").read_text(encoding="utf-8")

    check("no top-level doi in .zenodo.json", "doi" not in zenodo)
    check("upload_type is software", zenodo.get("upload_type") == "software")
    check("access_right is open", zenodo.get("access_right") == "open")
    creator = (zenodo.get("creators") or [{}])[0]
    check("creator affiliation is the canonical string",
          creator.get("affiliation") == AFFILIATION, creator.get("affiliation", ""))
    check("creator carries the ORCID", creator.get("orcid") == ORCID)

    version = zenodo.get("version")
    check("CITATION.cff version matches .zenodo.json",
          bool(version) and f"version: {version}" in citation, str(version))

    released_on = re.search(r'date-released:\s*"?(\d{4}-\d{2}-\d{2})"?', citation)
    today = datetime.date.today().isoformat()
    check("CITATION.cff date-released is today",
          bool(released_on) and released_on.group(1) == today,
          f"{released_on.group(1) if released_on else 'absent'} vs {today}")

    has_doi = bool(re.search(r"^doi:\s*\"10\.5281/zenodo\.\d+\"", citation, re.M))
    if released:
        check("CITATION.cff carries the concept DOI", has_doi)
    else:
        check("CITATION.cff concept DOI is still a placeholder", not has_doi)

    tracked = set(git("ls-files", "results").split())
    loads = set(re.findall(r'_load\("([^"]+)"\)',
                           (REPO / "paper/collect_results.py").read_text(encoding="utf-8")))
    missing = sorted(f"results/{name}" for name in loads if f"results/{name}" not in tracked)
    check("every result file the manifest loads is tracked", not missing, str(missing))

    check("working tree is clean", not git("status", "--porcelain"))
    ahead = git("rev-list", "--count", "origin/main..HEAD")
    check("nothing is unpushed", ahead in ("", "0"), f"{ahead} ahead")

    tags = git("tag").split()
    if released:
        check("the release tag exists", f"v{version}" in tags, str(tags))
    else:
        check("the release tag does not exist yet", f"v{version}" not in tags, str(tags))

    print()
    if failures:
        print(f"NOT READY: {len(failures)} check(s) failed")
        return 1
    print("ALL GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
