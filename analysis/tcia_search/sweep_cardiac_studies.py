"""Which public CT sessions contain a cardiac acquisition alongside other CT series?

BodyPartExamined is operator-filled and frequently blank, so filtering on HEART alone
understates the answer. StudyDescription is written by the protocol and survives
de-identification, so this sweeps every collection that holds CT and keeps the studies whose
description names a cardiac examination. Those studies are where a recorded heart rate can
sit next to a free-running helical chest scan.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
HERE = Path(__file__).resolve().parent
BODYPARTS = HERE / "tcia_bodyparts.json"
OUT = HERE / "tcia_cardiac_studies.json"

CARDIAC_WORDS = ("CARDIAC", "CORONARY", "CARDIO", "CTA HEART", "HEART", "CALCIUM",
                 "CA SCORE", "CASCORE", "CT ANGIO HEART", "GATED")


def get(endpoint: str, **params):
    url = f"{BASE}/{endpoint}?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=180) as response:
                body = response.read().decode("utf-8")
            return json.loads(body) if body.strip() else []
        except Exception as error:                      # noqa: BLE001 - network, retried
            if attempt == 2:
                return {"__error__": str(error)}
            time.sleep(3 * (attempt + 1))
    return {"__error__": "unreachable"}


def main() -> int:
    body_parts = json.loads(BODYPARTS.read_text(encoding="utf-8"))
    # A collection whose CT query returned nothing has no CT at all: verified against
    # getModalityValues for three of them, all MR/CR/RTSTRUCT only.
    with_ct = sorted(c for c, v in body_parts.items() if "body_parts" in v)
    print(f"{len(with_ct)} collections hold CT", flush=True)

    hits, errors = [], []
    for index, collection in enumerate(with_ct, 1):
        studies = get("getPatientStudy", Collection=collection)
        if isinstance(studies, dict):
            errors.append(collection)
            continue
        for study in studies:
            description = (study.get("StudyDescription") or "").upper()
            if any(word in description for word in CARDIAC_WORDS):
                hits.append({
                    "collection": collection,
                    "patient": study.get("PatientID"),
                    "study_uid": study.get("StudyInstanceUID"),
                    "study_description": study.get("StudyDescription"),
                    "series_count": study.get("SeriesCount"),
                    "study_date": study.get("StudyDate"),
                })
        if index % 20 == 0:
            print(f"  {index}/{len(with_ct)}  hits so far: {len(hits)}", flush=True)

    if errors:
        print(f"WARNING: {len(errors)} collections failed: {errors}", file=sys.stderr)

    OUT.write_text(json.dumps({"collections_queried": len(with_ct),
                               "collections_failed": errors,
                               "studies": hits}, indent=1, ensure_ascii=False),
                   encoding="utf-8")

    print(f"\ncollections queried: {len(with_ct)} | failed: {len(errors)}")
    print(f"studies whose description names a cardiac examination: {len(hits)}")
    by_collection = {}
    for hit in hits:
        by_collection.setdefault(hit["collection"], []).append(hit)
    for collection, rows in sorted(by_collection.items(), key=lambda kv: -len(kv[1])):
        multi = [r for r in rows if (r["series_count"] or 0) > 1]
        print(f"  {collection}: {len(rows)} studies ({len(multi)} with more than one series)")
        for row in rows[:3]:
            print(f"      {row['patient']}  {row['study_description']}  "
                  f"series={row['series_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
