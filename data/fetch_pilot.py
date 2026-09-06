"""Fetch the pilot series, chosen to span the table speeds the headers revealed.

The six collections that kept their spiral parameters run from 33.6 to 129 mm/s, and the
window predicts different answers across that range: at the cardiac border alone the slow
protocols record several cardiac cycles and the fast ones record barely one. Picking a
series from each end and one from the middle makes the pilot a test of that prediction
rather than a demonstration on a favourable case.

Series are selected on their headers before any pixel is read, and identified by UID.
Nothing is redistributed.

    python data/fetch_pilot.py --list        # choose and print, download nothing
    python data/fetch_pilot.py               # download the chosen series
"""

from __future__ import annotations

import argparse
import io
import json
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pydicom

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / "data_cache"
RESULTS = HERE.parent / "results"
API = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"

#: Chosen from the probe: slow, middle and fast, so the pilot spans the range rather than
#: sampling the easy end of it.
PILOT = [
    ("Anti-PD-1_Lung", "slow: 33.6 mm/s, threshold 42 bpm at the cardiac border"),
    ("RIDER Lung CT", "middle: 55.0 mm/s, threshold 69 bpm"),
    # QIN LUNG CT was the first choice for the fast arm and none of its thin series met
    # the criteria, so the fastest protocol in the probe takes that place instead. It is
    # the harder test of the prediction, not the easier one.
    ("COVID-19-NY-SBU", "fast: 129.0 mm/s, threshold 161 bpm -- predicted to fail"),
]

MIN_IMAGES = 150
#: An upper bound as well as a lower one. The largest series in a collection can be a
#: whole-body acquisition of over a gigabyte, and the pilot needs a chest, not the
#: biggest download available.
MAX_IMAGES = 800
MAX_INTERVAL_MM = 1.5


def _json(endpoint: str, **parameters):
    url = API + endpoint + "?" + urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(url, timeout=180) as response:
        return json.load(response)


def _one_header(series_uid: str):
    instances = _json("getSOPInstanceUIDs", SeriesInstanceUID=series_uid)
    if not instances:
        return None
    url = API + "getSingleImage?" + urllib.parse.urlencode(
        {"SeriesInstanceUID": series_uid,
         "SOPInstanceUID": instances[len(instances) // 2]["SOPInstanceUID"]}
    )
    with urllib.request.urlopen(url, timeout=300) as response:
        raw = response.read()
    return pydicom.dcmread(io.BytesIO(raw), stop_before_pixels=True)


def choose(collection: str):
    """The largest thin-slice series that still carries the parameters the window needs."""
    series = _json("getSeries", Collection=collection, Modality="CT")
    series.sort(key=lambda item: int(item.get("ImageCount", 0) or 0), reverse=True)
    for item in series[:40]:
        count = int(item.get("ImageCount", 0) or 0)
        if not MIN_IMAGES <= count <= MAX_IMAGES:
            continue
        try:
            header = _one_header(item["SeriesInstanceUID"])
        except Exception:  # noqa: BLE001 - a series that will not open is simply skipped
            continue
        if header is None:
            continue
        interval = getattr(header, "SpacingBetweenSlices", None) or \
            getattr(header, "SliceThickness", None)
        speed = getattr(header, "TableSpeed", None)
        if speed is None:
            pitch = getattr(header, "SpiralPitchFactor", None)
            rotation = getattr(header, "RevolutionTime", None)
            collimation = getattr(header, "TotalCollimationWidth", None)
            if None not in (pitch, rotation, collimation):
                speed = float(pitch) * float(collimation) / float(rotation)
        if interval is None or speed is None or float(interval) > MAX_INTERVAL_MM:
            continue
        return {
            "collection": collection,
            "patient": item.get("PatientID"),
            "series_uid": item["SeriesInstanceUID"],
            "model": item.get("ManufacturerModelName"),
            "licence": item.get("LicenseName"),
            "images": int(item.get("ImageCount", 0) or 0),
            "file_size_mb": round(float(item.get("FileSize", 0) or 0) / 1e6, 1),
            "reconstruction_interval_mm": float(interval),
            "table_speed_mm_s": float(speed),
            "contrast_agent": getattr(header, "ContrastBolusAgent", None) or None,
        }
        time.sleep(0.4)
    return None


def download(record: dict) -> Path:
    """Fetch the series as a zip and unpack it under data_cache/, by UID."""
    destination = CACHE / record["series_uid"]
    if destination.is_dir() and any(destination.iterdir()):
        print(f"    already present: {destination.name[:24]}...")
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    url = API + "getImage?" + urllib.parse.urlencode(
        {"SeriesInstanceUID": record["series_uid"]}
    )
    with urllib.request.urlopen(url, timeout=1800) as response:
        raw = response.read()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        archive.extractall(destination)
    print(f"    {len(raw) / 1e6:.0f} MB, {len(list(destination.iterdir()))} files")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="choose but download nothing")
    arguments = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    chosen = []
    for collection, why in PILOT:
        print(f"--- {collection}  ({why})")
        record = choose(collection)
        if record is None:
            print("    no series met the criteria")
            continue
        record["chosen_because"] = why
        chosen.append(record)
        print(f"    {record['patient']}  {record['images']} images, "
              f"{record['file_size_mb']} MB, {record['reconstruction_interval_mm']} mm, "
              f"S = {record['table_speed_mm_s']:.1f} mm/s")

    (RESULTS / "pilot_series.json").write_text(
        json.dumps(chosen, indent=2), encoding="utf-8"
    )
    total = sum(r["file_size_mb"] for r in chosen)
    print(f"\n{len(chosen)} series, {total:.0f} MB total")

    if arguments.list:
        return 0

    CACHE.mkdir(exist_ok=True)
    for record in chosen:
        print(f"\ndownloading {record['collection']} / {record['patient']}")
        download(record)
    print(f"\ncached under: {CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
