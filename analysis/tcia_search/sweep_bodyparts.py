"""Which TCIA collections contain CT of the heart at all?

A gated cardiac CT records BodyPartExamined = HEART. A collection that has no heart CT
cannot contain the pairing we are looking for, so this is the cheap filter that decides
where to spend the expensive queries.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
OUT = Path(__file__).resolve().parent / "tcia_bodyparts.json"


def get(endpoint: str, **params):
    url = f"{BASE}/{endpoint}?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:                      # noqa: BLE001 - network, retried
            if attempt == 2:
                return {"__error__": str(error)}
            time.sleep(2 * (attempt + 1))
    return {"__error__": "unreachable"}


def main() -> int:
    collections = [c["Collection"] for c in get("getCollectionValues")]
    print(f"{len(collections)} collections", flush=True)

    result = {}
    errors = 0
    for index, collection in enumerate(collections, 1):
        parts = get("getBodyPartValues", Collection=collection, Modality="CT")
        if isinstance(parts, dict):
            errors += 1
            result[collection] = {"error": parts.get("__error__")}
            continue
        values = sorted(p["BodyPartExamined"] for p in parts if p.get("BodyPartExamined"))
        result[collection] = {"body_parts": values}
        if index % 25 == 0:
            print(f"  {index}/{len(collections)}", flush=True)

    # A network failure that quietly shrinks the candidate list is the failure mode here.
    if errors:
        print(f"WARNING: {errors} collections could not be queried", file=sys.stderr)

    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")

    heart = {c: v["body_parts"] for c, v in result.items()
             if "body_parts" in v and any("HEART" in b.upper() for b in v["body_parts"])}
    print(f"\ncollections queried: {len(result)} | errors: {errors}")
    print(f"collections with a HEART CT series: {len(heart)}")
    for collection, parts in sorted(heart.items()):
        print(f"  {collection}: {', '.join(parts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
