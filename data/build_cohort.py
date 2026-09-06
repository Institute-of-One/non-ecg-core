"""Grow the pilot into a cohort, in two phases that cost very different amounts.

Three series is a pilot and cannot carry a claim. What the paper needs are two different
things, and only one of them needs pixels:

* **how the installed base is distributed.** That is a statement about scan parameters and
  comes from headers alone, one slice per series, about half a megabyte each. Hundreds are
  affordable.
* **how often the period is actually recovered.** That needs images, and is therefore
  sampled rather than exhaustive -- stratified across the table speeds the headers reveal,
  so the cohort spans the window rather than clustering where it works.

    python data/build_cohort.py --headers-only     # phase A, cheap
    python data/build_cohort.py --images 15        # phase A then phase B
"""

from __future__ import annotations

import argparse
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pydicom

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / "data_cache"
RESULTS = HERE.parent / "results"
API = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"

#: The collections the probe found still carrying the spiral parameters. The seven that do
#: not are excluded here for that reason and not for any property of their images.
COLLECTIONS = [
    "Anti-PD-1_Lung",
    "RIDER Lung CT",
    "CPTAC-LUAD",
    "Lung-PET-CT-Dx",
    "QIN LUNG CT",
    "COVID-19-NY-SBU",
]

MIN_IMAGES, MAX_IMAGES = 150, 800
MAX_INTERVAL_MM = 1.5
PER_COLLECTION = 40
DELAY_SECONDS = 0.4


def _json(endpoint: str, **parameters):
    url = API + endpoint + "?" + urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(url, timeout=180) as response:
        return json.load(response)


def _header(series_uid: str):
    instances = _json("getSOPInstanceUIDs", SeriesInstanceUID=series_uid)
    if not instances:
        return None
    url = API + "getSingleImage?" + urllib.parse.urlencode(
        {"SeriesInstanceUID": series_uid,
         "SOPInstanceUID": instances[len(instances) // 2]["SOPInstanceUID"]}
    )
    with urllib.request.urlopen(url, timeout=300) as response:
        return pydicom.dcmread(io.BytesIO(response.read()), stop_before_pixels=True)


def _table_speed(header):
    speed = getattr(header, "TableSpeed", None)
    if speed is not None:
        return float(speed)
    pitch = getattr(header, "SpiralPitchFactor", None)
    rotation = getattr(header, "RevolutionTime", None)
    collimation = getattr(header, "TotalCollimationWidth", None)
    if None not in (pitch, rotation, collimation):
        return float(pitch) * float(collimation) / float(rotation)
    feed = getattr(header, "TableFeedPerRotation", None)
    if feed is not None and rotation is not None:
        return float(feed) / float(rotation)
    return None


def harvest_headers() -> list[dict]:
    records = []
    for collection in COLLECTIONS:
        try:
            series = _json("getSeries", Collection=collection, Modality="CT")
        except Exception as error:  # noqa: BLE001
            print(f"{collection}: unreachable, {error}")
            continue
        series.sort(key=lambda item: int(item.get("ImageCount", 0) or 0), reverse=True)
        taken = 0
        for item in series:
            if taken >= PER_COLLECTION:
                break
            count = int(item.get("ImageCount", 0) or 0)
            if not MIN_IMAGES <= count <= MAX_IMAGES:
                continue
            try:
                header = _header(item["SeriesInstanceUID"])
            except Exception:  # noqa: BLE001 - unreadable series are simply not counted
                continue
            if header is None:
                continue
            interval = getattr(header, "SpacingBetweenSlices", None) or \
                getattr(header, "SliceThickness", None)
            speed = _table_speed(header)
            if interval is None or speed is None or float(interval) > MAX_INTERVAL_MM:
                continue
            records.append({
                "collection": collection,
                "patient": item.get("PatientID"),
                "series_uid": item["SeriesInstanceUID"],
                "model": item.get("ManufacturerModelName"),
                "licence": item.get("LicenseName"),
                "images": count,
                "file_size_mb": round(float(item.get("FileSize", 0) or 0) / 1e6, 1),
                "reconstruction_interval_mm": float(interval),
                "table_speed_mm_s": speed,
                "contrast_agent": getattr(header, "ContrastBolusAgent", None) or None,
            })
            taken += 1
            time.sleep(DELAY_SECONDS)
        print(f"{collection:22} {taken:>3} series with usable parameters")
    return records


def stratify(records: list[dict], wanted: int) -> list[dict]:
    """Spread the image cohort across the table speeds, not across the collections.

    Sampling per collection would over-represent whichever archive happens to be largest.
    The quantity the window is a condition on is table speed, so that is what the strata
    are cut on: the cohort has to span the range it is being used to test.
    """
    ordered = sorted(records, key=lambda record: record["table_speed_mm_s"])
    if len(ordered) <= wanted:
        return ordered
    picks, seen = [], set()
    for position in range(wanted):
        index = round(position * (len(ordered) - 1) / max(wanted - 1, 1))
        while index in seen and index < len(ordered) - 1:
            index += 1
        seen.add(index)
        picks.append(ordered[index])
    return picks


def download(record: dict) -> bool:
    destination = CACHE / record["series_uid"]
    if destination.is_dir() and any(destination.iterdir()):
        return True
    destination.mkdir(parents=True, exist_ok=True)
    url = API + "getImage?" + urllib.parse.urlencode(
        {"SeriesInstanceUID": record["series_uid"]}
    )
    try:
        with urllib.request.urlopen(url, timeout=2400) as response:
            raw = response.read()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            archive.extractall(destination)
    except Exception as error:  # noqa: BLE001 - a failed download must not stop the cohort
        print(f"    FAILED {record['patient']}: {error}")
        return False
    print(f"    {record['collection']:22} {record['patient']:<18} "
          f"S={record['table_speed_mm_s']:6.1f}  {len(raw) / 1e6:.0f} MB")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headers-only", action="store_true")
    parser.add_argument("--images", type=int, default=15)
    arguments = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    print("=== phase A: headers")
    records = harvest_headers()
    (RESULTS / "cohort_headers.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    speeds = sorted(r["table_speed_mm_s"] for r in records)
    if speeds:
        print(f"\n{len(records)} series, table speed {speeds[0]:.1f} to {speeds[-1]:.1f} mm/s, "
              f"median {speeds[len(speeds) // 2]:.1f}")

    if arguments.headers_only or not records:
        return 0

    chosen = stratify(records, arguments.images)
    (RESULTS / "cohort_images.json").write_text(
        json.dumps(chosen, indent=2), encoding="utf-8"
    )
    total = sum(r["file_size_mb"] for r in chosen)
    print(f"\n=== phase B: images for {len(chosen)} series, about {total:.0f} MB")
    for record in chosen:
        download(record)
    print(f"\ncached under: {CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
