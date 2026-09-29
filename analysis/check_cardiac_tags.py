"""Does any analysed series carry a recorded cardiac rate, by any route?

The paper's premise is that a non-gated chest CT does not record the patient's heart rate,
so an estimate made from such a scan cannot be checked against a recorded truth. That
premise was asserted rather than measured. This measures it over the series whose images the
cohort analysis actually read, and writes the count the manuscript is allowed to quote.

Two routes are checked, because the first version of this script only knew about the first
and would have supported a claim that was too strong:

1. The standard DICOM cardiac fields (HeartRate, NominalInterval, the R-R bounds, and the
   rest of the gating group).
2. Free text in ScanOptions (0018,0022). A Siemens cardiac acquisition writes the rate there
   as OSCRATEMIN072BPM / OSCRATEMAX078BPM / OSCRATEAVG075BPM while leaving HeartRate empty.
   Found on 2026-09-29 in TCIA VAREPOP-APOLLO patient AP-26JK, whose CARDIAC CTA session
   also contains a free-running helical chest series ten seconds later. A survey that looked
   only at route 1 would have reported that no public CT records the rate, which is false.

It is a descriptive check of the data, not a decision rule: it changes nothing that was
frozen before the cohort was fitted. Added after PMB's board member observed that the cohort
analysis has no reference heart rate.

    python analysis/check_cardiac_tags.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pydicom

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / "data_cache"
OUT = HERE.parent / "results" / "cardiac_tags.json"

# Every standard DICOM field in which an acquisition can record cardiac timing.
TAGS = {
    "HeartRate": (0x0018, 0x1088),
    "NominalInterval": (0x0018, 0x1062),
    "LowRRValue": (0x0018, 0x1081),
    "HighRRValue": (0x0018, 0x1082),
    "IntervalsAcquired": (0x0018, 0x1083),
    "IntervalsRejected": (0x0018, 0x1084),
    "CardiacNumberOfImages": (0x0018, 0x1090),
    "TriggerTime": (0x0018, 0x1060),
    "CardiacSynchronizationTechnique": (0x0018, 0x9037),
    "CardiacRRIntervalSpecified": (0x0018, 0x9070),
}

SCAN_OPTIONS = (0x0018, 0x0022)
# OSCRATEAVG075BPM and its MIN/MAX siblings; the trailing unit is what makes it a rate.
RATE_IN_TEXT = re.compile(r"(OSCRATE(?:MIN|MAX|AVG)?)\s*0*(\d{2,3})\s*BPM", re.IGNORECASE)


def _instances(series_dir: Path) -> list[Path]:
    """First, middle and last instance: a field written by only part of a series still shows."""
    files = sorted(series_dir.glob("*.dcm"))
    if not files:
        return []
    return sorted({files[0], files[len(files) // 2], files[-1]})


def _rates_in_scan_options(header) -> dict:
    if SCAN_OPTIONS not in header:
        return {}
    text = str(header[SCAN_OPTIONS].value)
    return {match.group(1).upper(): int(match.group(2)) for match in RATE_IN_TEXT.finditer(text)}


def main() -> int:
    series_dirs = sorted(p for p in CACHE.iterdir() if p.is_dir())
    if not series_dirs:
        raise SystemExit(f"no cached series under {CACHE}")

    per_series = []
    for series_dir in series_dirs:
        instances = _instances(series_dir)
        if not instances:
            continue
        standard, from_text, scan_options = {}, {}, None
        for path in instances:
            header = pydicom.dcmread(path, stop_before_pixels=True)
            for name, tag in TAGS.items():
                if tag in header:
                    value = str(header[tag].value).strip()
                    if value and value != "None":
                        standard[name] = value
            if SCAN_OPTIONS in header:
                scan_options = str(header[SCAN_OPTIONS].value)
            from_text.update(_rates_in_scan_options(header))
        per_series.append({
            "series_uid": series_dir.name,
            "instances_read": len(instances),
            "standard_cardiac_fields": standard,
            "scan_options": scan_options,
            "rates_in_scan_options": from_text,
        })

    # A silent zero here would read exactly like a clean negative result.
    if len(per_series) != len(series_dirs):
        raise SystemExit(
            f"read {len(per_series)} series but {len(series_dirs)} are cached; "
            "a series produced no readable instance"
        )

    with_standard = [s for s in per_series if s["standard_cardiac_fields"]]
    with_text = [s for s in per_series if s["rates_in_scan_options"]]
    with_any = [s for s in per_series
                if s["standard_cardiac_fields"] or s["rates_in_scan_options"]]
    result = {
        "checked_on": "2026-09-29",
        "routes_checked": len(TAGS) + 1,
        "tags_checked": {name: f"{tag[0]:04X},{tag[1]:04X}" for name, tag in TAGS.items()},
        "free_text_field": "ScanOptions (0018,0022), searched for a rate in bpm",
        "series_checked": len(per_series),
        "series_with_standard_field": len(with_standard),
        "series_with_rate_in_scan_options": len(with_text),
        "series_with_any_cardiac_field": len(with_any),
        "per_tag_present": {
            name: sum(1 for s in per_series if name in s["standard_cardiac_fields"])
            for name in TAGS
        },
        "series": per_series,
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"series checked: {result['series_checked']}")
    print(f"  with a standard cardiac field:     {result['series_with_standard_field']}")
    print(f"  with a rate written in ScanOptions:{result['series_with_rate_in_scan_options']:>3}")
    print(f"  with a recorded rate by any route: {result['series_with_any_cardiac_field']}")
    print(f"\nwritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
