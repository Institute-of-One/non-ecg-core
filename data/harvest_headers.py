"""Read one slice per series to learn what the installed base actually does.

Two things come from this and neither needs a whole image volume. Where practice sits
relative to the window is a statement about scan parameters, and scan parameters are in
the header; and the pilot series for step 4 have to be chosen on their headers before
anything is looked at, which is what the frozen protocol requires.

One instance per series is fetched rather than the series, which is about 0.5 MB instead
of several hundred. Nothing is redistributed: series are identified by UID.

    python data/harvest_headers.py --limit 40      # sample 40 series
    python data/harvest_headers.py --report        # re-read what was harvested
"""

from __future__ import annotations

import argparse
import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pydicom

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
HEADERS = RESULTS / "lidc_headers.json"

API = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"
COLLECTION = "LIDC-IDRI"
DELAY_SECONDS = 0.5

#: The heart's z extent is what the cardiac border can write on; the descending aorta runs
#: much further. Both are needed to say whether a series can carry the signal at all.
HEART_EXTENT_MM = 120.0


def _get_json(endpoint: str, **parameters):
    url = API + endpoint + "?" + urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(url, timeout=180) as response:
        return json.load(response)


def _get_bytes(endpoint: str, **parameters) -> bytes:
    url = API + endpoint + "?" + urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(url, timeout=300) as response:
        return response.read()


def read_one_slice(series_uid: str):
    """Fetch a single instance from the middle of the series and parse its header."""
    instances = _get_json("getSOPInstanceUIDs", SeriesInstanceUID=series_uid)
    if not instances:
        return None
    middle = instances[len(instances) // 2]["SOPInstanceUID"]
    # getSingleImage needs the series as well as the instance; with the instance alone it
    # answers 400 with an empty reason, which reads like a bad UID rather than a missing
    # parameter and cost a full run to find.
    raw = _get_bytes("getSingleImage", SeriesInstanceUID=series_uid, SOPInstanceUID=middle)
    return pydicom.dcmread(io.BytesIO(raw), stop_before_pixels=True)


def describe(dataset, series: dict) -> dict:
    """The scan parameters the window is a condition on, plus enough to select on."""

    def value(name, default=None):
        got = getattr(dataset, name, default)
        try:
            return float(got)
        except (TypeError, ValueError):
            return got if got is None or isinstance(got, str) else default

    pitch = value("SpiralPitchFactor")
    rotation = value("RevolutionTime")
    total_collimation = value("TotalCollimationWidth")
    single_collimation = value("SingleCollimationWidth")
    table_speed = value("TableSpeed")
    thickness = value("SliceThickness")
    spacing = value("SpacingBetweenSlices")

    # Table speed is the quantity the window is written in. Prefer the tag; otherwise
    # derive it, and record which happened so a derived number is never mistaken for a
    # measured one.
    source = "TableSpeed tag"
    if table_speed is None:
        if None not in (pitch, rotation, total_collimation):
            table_speed = pitch * total_collimation / rotation
            source = "derived from pitch x collimation / rotation"
        else:
            source = "unavailable"

    interval = spacing if spacing else thickness
    images = int(series.get("ImageCount", 0) or 0)
    z_extent = images * interval if interval else None

    return {
        "patient": series.get("PatientID"),
        "series_uid": series.get("SeriesInstanceUID"),
        "manufacturer": series.get("Manufacturer"),
        "model": series.get("ManufacturerModelName"),
        "licence": series.get("LicenseName"),
        "images": images,
        "slice_thickness_mm": thickness,
        "spacing_between_slices_mm": spacing,
        "reconstruction_interval_mm": interval,
        "scanned_z_extent_mm": z_extent,
        "spiral_pitch_factor": pitch,
        "revolution_time_s": rotation,
        "total_collimation_mm": total_collimation,
        "single_collimation_mm": single_collimation,
        "table_speed_mm_s": table_speed,
        "table_speed_source": source,
        "kvp": value("KVP"),
        "contrast_agent": getattr(dataset, "ContrastBolusAgent", None) or None,
        "kernel": getattr(dataset, "ConvolutionKernel", None),
    }


def threshold_bpm(record: dict, cycles_needed: float, extent_mm: float):
    speed = record.get("table_speed_mm_s")
    if not speed or not extent_mm:
        return None
    return 60.0 * speed * cycles_needed / extent_mm


def harvest(limit: int) -> dict:
    series = _get_json("getSeries", Collection=COLLECTION, Modality="CT")
    # Thin reconstructions carry more slices for the same anatomy, so sampling from the
    # top of the image count reaches the series the pilot needs. The distribution over all
    # 1018 is reported separately and is not biased by this ordering.
    series.sort(key=lambda item: int(item.get("ImageCount", 0) or 0), reverse=True)
    chosen = series[:limit]

    records, failures = [], []
    for index, item in enumerate(chosen, start=1):
        try:
            dataset = read_one_slice(item["SeriesInstanceUID"])
            if dataset is None:
                failures.append({"series": item["SeriesInstanceUID"], "why": "no instances"})
                continue
            records.append(describe(dataset, item))
            last = records[-1]
            print(f"  {index:>3}/{len(chosen)}  {last['patient']:<16} "
                  f"{str(last['reconstruction_interval_mm']):>5} mm  "
                  f"pitch {str(last['spiral_pitch_factor']):>5}  "
                  f"S {str(round(last['table_speed_mm_s'], 1)) if last['table_speed_mm_s'] else '?':>7} mm/s")
        except Exception as error:  # noqa: BLE001 - a failed fetch must be visible
            failures.append({"series": item["SeriesInstanceUID"], "why": repr(error)})
            print(f"  {index:>3}/{len(chosen)}  FAILED {error}")
        time.sleep(DELAY_SECONDS)

    return {
        "collection": COLLECTION,
        "series_in_collection": len(series),
        "sampled": len(chosen),
        "harvested": len(records),
        "failures": failures,
        "records": records,
    }


def report(data: dict) -> None:
    records = data["records"]
    usable = [r for r in records if r.get("table_speed_mm_s")]
    print(f"\nharvested {len(records)} series, {len(usable)} with a usable table speed")
    if not usable:
        return

    speeds = sorted(r["table_speed_mm_s"] for r in usable)
    print(f"table speed: min {speeds[0]:.1f}, median {speeds[len(speeds)//2]:.1f}, "
          f"max {speeds[-1]:.1f} mm/s")

    for cycles in (2.5,):
        for extent, label in ((HEART_EXTENT_MM, "cardiac border, 120 mm"),
                              (None, "the scanned extent itself")):
            thresholds = []
            for record in usable:
                length = extent or record.get("scanned_z_extent_mm")
                value = threshold_bpm(record, cycles, length)
                if value:
                    thresholds.append(value)
            if not thresholds:
                continue
            thresholds.sort()
            below_100 = sum(1 for t in thresholds if t <= 100)
            print(f"\n  N_min={cycles}, {label}")
            print(f"    threshold heart rate: median {thresholds[len(thresholds)//2]:.0f} bpm, "
                  f"range {thresholds[0]:.0f}-{thresholds[-1]:.0f}")
            print(f"    series recording the period at or below 100 bpm: "
                  f"{below_100}/{len(thresholds)} ({below_100/len(thresholds):.0%})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--report", action="store_true")
    arguments = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    if arguments.report:
        if not HEADERS.is_file():
            print("nothing harvested yet")
            return 1
        report(json.loads(HEADERS.read_text(encoding="utf-8")))
        return 0

    data = harvest(arguments.limit)
    HEADERS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    report(data)
    print(f"\nwritten: {HEADERS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
