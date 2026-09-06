"""Find which public chest-CT collections still carry the spiral parameters.

The window is a condition on table speed, which comes from spiral pitch factor, total
collimation and revolution time. LIDC-IDRI carries none of them: its scanners predate the
CT acquisition modules that hold them, so a series can be perfect for measuring the aortic
signal and still say nothing about where practice sits.

That is a constraint on collection choice, and it is invisible until a header is opened.
This probe opens one slice per collection and reports which tags survived, so the choice is
made on evidence rather than on which collection is famous.

    python data/probe_collections.py
"""

from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pydicom

RESULTS = Path(__file__).resolve().parent.parent / "results"
API = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"

#: Chest or thorax CT collections spanning two decades of scanner generations, so the
#: answer is about when the tags appear rather than about one archive's habits.
CANDIDATES = [
    "LIDC-IDRI",
    "NSCLC-Radiomics",
    "NSCLC Radiogenomics",
    "LungCT-Diagnosis",
    "QIN LUNG CT",
    "CPTAC-LUAD",
    "COVID-19-NY-SBU",
    "COVID-19-AR",
    "Anti-PD-1_Lung",
    "TCGA-LUAD",
    "RIDER Lung CT",
    "SPIE-AAPM Lung CT Challenge",
    "Lung-PET-CT-Dx",
]

#: What the window needs, and the older tags that can stand in for parts of it.
WANTED = [
    ("SpiralPitchFactor", "0018,9311"),
    ("TableSpeed", "0018,9309"),
    ("TableFeedPerRotation", "0018,9310"),
    ("RevolutionTime", "0018,9305"),
    ("TotalCollimationWidth", "0018,9307"),
    ("SingleCollimationWidth", "0018,9306"),
    ("ExposureTime", "0018,1150"),
    ("XRayTubeCurrent", "0018,1151"),
    ("Exposure", "0018,1152"),
    ("SliceThickness", "0018,0050"),
    ("SpacingBetweenSlices", "0018,0088"),
]


def _json(endpoint: str, **parameters):
    url = API + endpoint + "?" + urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(url, timeout=180) as response:
        return json.load(response)


def one_header(collection: str):
    series = _json("getSeries", Collection=collection, Modality="CT")
    if not series:
        return None, None
    series.sort(key=lambda item: int(item.get("ImageCount", 0) or 0), reverse=True)
    chosen = series[0]
    instances = _json("getSOPInstanceUIDs", SeriesInstanceUID=chosen["SeriesInstanceUID"])
    if not instances:
        return None, chosen
    url = API + "getSingleImage?" + urllib.parse.urlencode(
        {"SeriesInstanceUID": chosen["SeriesInstanceUID"],
         "SOPInstanceUID": instances[len(instances) // 2]["SOPInstanceUID"]}
    )
    with urllib.request.urlopen(url, timeout=300) as response:
        raw = response.read()
    return pydicom.dcmread(io.BytesIO(raw), stop_before_pixels=True), chosen


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    findings = []
    header = "collection".ljust(22) + "".join(name[:11].rjust(12) for name, _ in WANTED[:6])
    print(header)
    for collection in CANDIDATES:
        try:
            dataset, series = one_header(collection)
        # An unknown collection answers 200 with an empty body, so the JSON decode is
        # where a wrong name shows up -- not as an HTTP error.
        except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                json.JSONDecodeError) as error:
            print(f"{collection[:22]:<22} unreachable: {error}")
            findings.append({"collection": collection, "error": repr(error)})
            continue
        if dataset is None:
            print(f"{collection[:22]:<22} no CT series")
            findings.append({"collection": collection, "error": "no CT series"})
            continue
        present = {name: getattr(dataset, name, None) for name, _ in WANTED}
        record = {
            "collection": collection,
            "model": series.get("ManufacturerModelName"),
            "images": series.get("ImageCount"),
            "tags": {name: (None if value is None else str(value)) for name, value in present.items()},
            "has_window_parameters": all(
                present.get(name) is not None
                for name in ("SpiralPitchFactor", "RevolutionTime", "TotalCollimationWidth")
            ) or present.get("TableSpeed") is not None,
        }
        findings.append(record)
        cells = "".join(
            (str(present[name])[:11] if present[name] is not None else "-").rjust(12)
            for name, _ in WANTED[:6]
        )
        print(f"{collection[:22]:<22}{cells}")
        time.sleep(0.5)

    destination = RESULTS / "collection_probe.json"
    destination.write_text(json.dumps(findings, indent=2), encoding="utf-8")

    usable = [f for f in findings if f.get("has_window_parameters")]
    print(f"\ncollections carrying enough to compute table speed: {len(usable)}")
    for record in usable:
        print(f"  {record['collection']}  ({record['model']})")
    print(f"\nwritten: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
