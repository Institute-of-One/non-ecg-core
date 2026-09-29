"""For every patient with a cardiac CT session, is there a recorded rate and a helical chest scan?

A cardiac study description is only a lead. The pairing this looks for is, on one date:
a series whose header records the heart rate (standard fields, or a Siemens rate written
into ScanOptions), and a free-running helical series covering the chest that could carry the
period along z. One instance per series answers both.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pydicom

BASE = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "probe_cache"
STUDIES = HERE / "tcia_cardiac_studies.json"
OUT = HERE / "tcia_pairings.json"

RATE = re.compile(r"(OSCRATE(?:MIN|MAX|AVG)?)\s*0*(\d{2,3})\s*BPM", re.IGNORECASE)
STANDARD = {"HeartRate": (0x0018, 0x1088), "NominalInterval": (0x0018, 0x1062),
            "LowRRValue": (0x0018, 0x1081), "HighRRValue": (0x0018, 0x1082)}
FIELDS = ["SeriesDescription", "StudyDescription", "AcquisitionTime", "SeriesTime",
          "Manufacturer", "ManufacturerModelName", "SpiralPitchFactor",
          "TableFeedPerRotation", "ExposureTime", "SliceThickness", "ScanOptions",
          "BodyPartExamined", "ImagePositionPatient"]


def get(endpoint: str, **params):
    url = f"{BASE}/{endpoint}?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=180) as response:
                body = response.read()
            if endpoint == "getSingleImage":
                return body
            text = body.decode("utf-8")
            return json.loads(text) if text.strip() else []
        except Exception as error:                       # noqa: BLE001 - network, retried
            if attempt == 2:
                return {"__error__": str(error)}
            time.sleep(3 * (attempt + 1))
    return {"__error__": "unreachable"}


def header_of(series_uid: str):
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{series_uid[-14:]}.dcm"
    if not path.exists():
        sops = get("getSOPInstanceUIDs", SeriesInstanceUID=series_uid)
        if isinstance(sops, dict) or not sops:
            return None
        blob = get("getSingleImage", SeriesInstanceUID=series_uid,
                   SOPInstanceUID=sops[0]["SOPInstanceUID"])
        if isinstance(blob, dict):
            return None
        path.write_bytes(blob)
    try:
        return pydicom.dcmread(path, stop_before_pixels=True)
    except Exception:                                    # noqa: BLE001 - reported below
        return None


def main() -> int:
    data = json.loads(STUDIES.read_text(encoding="utf-8"))
    wanted = [s for s in data["studies"]
              if (s["series_count"] or 0) > 1 and "ECHOCARDIOGRAM" not in
              (s["study_description"] or "").upper()]
    patients = sorted({(s["collection"], s["patient"]) for s in wanted})
    print(f"{len(wanted)} multi-series cardiac studies across {len(patients)} patients\n",
          flush=True)

    report, failures = [], 0
    for collection, patient in patients:
        series = get("getSeries", Collection=collection, PatientID=patient, Modality="CT")
        if isinstance(series, dict):
            failures += 1
            continue
        by_date = {}
        for entry in series:
            by_date.setdefault((entry.get("StudyDate") or "?")[:10], []).append(entry)

        for date, rows in sorted(by_date.items()):
            described = []
            for entry in rows:
                header = header_of(entry["SeriesInstanceUID"])
                if header is None:
                    failures += 1
                    continue
                values = {f: str(getattr(header, f)) for f in FIELDS
                          if getattr(header, f, None) not in (None, "")}
                rates = {m.group(1).upper(): int(m.group(2))
                         for m in RATE.finditer(values.get("ScanOptions", ""))}
                for name, tag in STANDARD.items():
                    if tag in header and str(header[tag].value).strip() not in ("", "None"):
                        rates[name] = str(header[tag].value)
                pitch = values.get("SpiralPitchFactor")
                described.append({
                    "series_uid": entry["SeriesInstanceUID"],
                    "images": entry["ImageCount"],
                    "body_part": entry.get("BodyPartExamined"),
                    "description": values.get("SeriesDescription"),
                    "acquisition_time": values.get("AcquisitionTime"),
                    "pitch": pitch,
                    "feed_mm_per_rotation": values.get("TableFeedPerRotation"),
                    "exposure_time_ms": values.get("ExposureTime"),
                    "model": values.get("ManufacturerModelName"),
                    "rates": rates,
                })
            with_rate = [d for d in described if d["rates"]]
            helical = [d for d in described
                       if d["pitch"] and float(d["pitch"]) >= 1.0 and not d["rates"]
                       and d["images"] > 50]
            if with_rate:
                report.append({
                    "collection": collection, "patient": patient, "date": date,
                    "series_with_recorded_rate": with_rate,
                    "free_running_helical_series": helical,
                    "pairing": bool(with_rate and helical),
                })
                mark = "PAIR " if (with_rate and helical) else "rate "
                print(f"{mark}{collection}/{patient} {date}: "
                      f"{len(with_rate)} with a rate, {len(helical)} helical pitch>=1",
                      flush=True)

    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    pairs = [r for r in report if r["pairing"]]
    print(f"\npatients probed: {len(patients)} | series that could not be read: {failures}")
    print(f"sessions with a recorded rate: {len(report)}")
    print(f"sessions with BOTH a recorded rate and a free-running helical series: {len(pairs)}")
    for row in pairs:
        rates = row["series_with_recorded_rate"][0]["rates"]
        print(f"  {row['collection']}/{row['patient']} {row['date']}  rate={rates}")
        for helix in row["free_running_helical_series"]:
            print(f"      helical: {helix['description']} n={helix['images']} "
                  f"pitch={helix['pitch']} feed={helix['feed_mm_per_rotation']} "
                  f"rot={helix['exposure_time_ms']}ms t={helix['acquisition_time']}")
    if failures:
        print(f"\nWARNING: {failures} series could not be read; "
              "the pairing count is a lower bound", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
