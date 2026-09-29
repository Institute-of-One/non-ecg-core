"""Run the frozen pipeline on the one public series whose heart rate is recorded.

The criterion below is fixed by analysis/tcia_search/validation_protocol.md, written before
this series was downloaded. It is repeated here as constants so that the comparison cannot
be adjusted after seeing the fit.

    python analysis/tcia_search/run_reference_case.py
"""

from __future__ import annotations

import io
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "analysis"))

BASE = "https://services.cancerimagingarchive.net/nbia-api/services/v1"

# ------------------------------------------------------------------- frozen before the run
SERIES_UID = "1.3.6.1.4.1.14519.5.2.1.264532322608206684963835753501167761257"
COLLECTION = "VAREPOP-APOLLO"
PATIENT = "AP-26JK"
REFERENCE_BPM = 75.0            # OSCRATEAVG075BPM, gated series of the same session
RECORDED_RANGE_BPM = (72.0, 78.0)   # OSCRATEMIN072BPM .. OSCRATEMAX078BPM
TOLERANCE = 0.05                # the tolerance N_min was measured under
BAND = (REFERENCE_BPM * (1 - TOLERANCE), REFERENCE_BPM * (1 + TOLERANCE))
# -----------------------------------------------------------------------------------------

OUT = REPO / "results" / "reference_case.json"


def fetch_series(destination: Path) -> int:
    """The whole series as one ZIP; NBIA offers no bulk header-only route."""
    if destination.is_dir() and any(destination.glob("*.dcm")):
        return len(list(destination.glob("*.dcm")))
    destination.mkdir(parents=True, exist_ok=True)
    url = f"{BASE}/getImage?" + urllib.parse.urlencode({"SeriesInstanceUID": SERIES_UID})
    print(f"downloading {SERIES_UID[-12:]} ...", flush=True)
    with urllib.request.urlopen(url, timeout=1800) as response:
        blob = response.read()
    print(f"  {len(blob) / 1e6:.0f} MB", flush=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        members = [n for n in archive.namelist() if n.lower().endswith(".dcm")]
        for name in members:
            (destination / Path(name).name).write_bytes(archive.read(name))
    return len(members)


def main() -> int:
    from run_cohort import analyse_series          # the frozen pipeline, unmodified

    directory = REPO / "data_cache" / SERIES_UID
    count = fetch_series(directory)
    print(f"instances on disk: {count}\n", flush=True)

    outcome = analyse_series(directory)

    if "technical_failure" in outcome:
        verdict = "technical failure"
        agrees = None
    else:
        rate = outcome["heart_rate_bpm"]
        agrees = BAND[0] <= rate <= BAND[1]
        verdict = "rate in agreement" if agrees else "rate in disagreement"

    result = {
        "protocol": "analysis/tcia_search/validation_protocol.md (frozen before download)",
        "collection": COLLECTION,
        "patient": PATIENT,
        "series_uid": SERIES_UID,
        "reference_bpm": REFERENCE_BPM,
        "recorded_range_bpm": list(RECORDED_RANGE_BPM),
        "tolerance": TOLERANCE,
        "agreement_band_bpm": list(BAND),
        "instances": count,
        "outcome": outcome,
        "primary_rate_in_agreement": agrees,
        "secondary_self_consistent": outcome.get("recovered"),
        "verdict": verdict,
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"reference rate      : {REFERENCE_BPM} bpm (recorded {RECORDED_RANGE_BPM[0]:.0f}"
          f"-{RECORDED_RANGE_BPM[1]:.0f})")
    print(f"agreement band      : {BAND[0]:.2f} - {BAND[1]:.2f} bpm")
    if "technical_failure" in outcome:
        print(f"TECHNICAL FAILURE   : {outcome['technical_failure']}")
    else:
        print(f"fitted rate         : {outcome['heart_rate_bpm']:.2f} bpm")
        print(f"cycles written      : {outcome['cycles_written']:.2f}  (N_min 2.5)")
        print(f"z span / speed      : {outcome['z_span_mm']:.0f} mm at "
              f"{outcome['table_speed_mm_s']:.1f} mm/s")
        print(f"leave-one-out       : spread {outcome['leave_one_out_spread_bpm']:.1f} bpm "
              f"from {[round(v, 1) for v in outcome['leave_one_out_bpm']]}")
        print(f"median sigma        : {outcome['median_sigma']:.3f}")
        print()
        print(f"PRIMARY   rate correct        : {agrees}")
        print(f"SECONDARY self-consistent     : {outcome['recovered']}"
              f"{'' if outcome['recovered'] else '  because ' + '; '.join(outcome['why_not'])}")
    print(f"\nwritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
