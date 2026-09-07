"""Gather every number the manuscript quotes, from the files that produced them.

A metric typed into prose is a metric that drifts from the run that made it. Every figure
in the manuscript is written as a marker and resolved from this manifest at build time, so
a number that cannot be traced back to a result file cannot reach the paper.

Writing this first also forces the claims to be enumerated before the prose is written:
if a quantity is not here, the manuscript may not assert it.

    python paper/collect_results.py
"""

from __future__ import annotations

import json
import statistics
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
MANIFEST = HERE / "frozen" / "manifest.json"


def _load(name: str):
    path = RESULTS / name
    if not path.is_file():
        raise SystemExit(f"missing result file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def simulation_metrics() -> dict:
    """N_min under each estimator, and how stable it is across the sweep."""
    out = {}
    central = _load("n_min.json")            # matched, the floor
    fundamental = _load("n_min_fundamental.json")

    out["n_min_matched"] = central["headline_n_min"]
    out["n_min_fundamental"] = fundamental["headline_n_min"]
    out["trials_per_cell"] = fundamental["criterion"]["trials"]
    out["tolerance_percent"] = round(fundamental["criterion"]["tolerance"] * 100)
    out["success_rate_percent"] = round(fundamental["criterion"]["success_rate"] * 100)

    cells = fundamental["sensitivity"]
    values = [c["n_min"] for c in cells if c["n_min"] is not None]
    out["sensitivity_cells"] = len(cells)
    out["cells_at_headline"] = sum(1 for v in values if v == out["n_min_fundamental"])
    out["n_min_worst_case"] = max(values)
    # the only regime where it degrades
    coarse = [c["n_min"] for c in cells
              if c["samples_per_cycle"] == 8 and c["noise"] == 0.40 and c["n_min"]]
    out["n_min_worst_coarse_sampling"] = max(coarse) if coarse else None
    return out


def header_metrics() -> dict:
    """What the installed base does, from headers alone."""
    cohort = _load("cohort_headers.json")
    speeds = sorted(r["table_speed_mm_s"] for r in cohort)
    out = {
        "header_series": len(cohort),
        "header_collections": len({r["collection"] for r in cohort}),
        "table_speed_min": round(min(speeds), 1),
        "table_speed_median": round(statistics.median(speeds), 1),
        "table_speed_max": round(max(speeds), 1),
        "table_speed_ratio": round(max(speeds) / min(speeds), 1),
    }
    n_min = 2.5
    for extent, label in ((120.0, "border"), (300.0, "aorta")):
        thresholds = [60.0 * s * n_min / extent for s in speeds]
        out[f"threshold_median_{label}"] = round(statistics.median(thresholds))
        out[f"threshold_min_{label}"] = round(min(thresholds))
        out[f"threshold_max_{label}"] = round(max(thresholds))
        below = sum(1 for t in thresholds if t <= 100)
        out[f"records_below_100bpm_{label}"] = below
        out[f"records_below_100bpm_{label}_percent"] = round(100 * below / len(thresholds))

    probe = _load("collection_probe.json")
    usable = [p for p in probe if p.get("has_window_parameters")]
    out["collections_probed"] = len([p for p in probe if "error" not in p])
    out["collections_with_parameters"] = len(usable)
    out["collections_without_parameters"] = out["collections_probed"] - len(usable)
    return out


def representative_protocol_metrics() -> dict:
    """Thresholds for the two protocols the 192 headers do not contain.

    Wide-detector and dual-source high-pitch acquisitions are the ones the bound excludes
    absolutely, and no series in the header cohort uses them, so their thresholds come from
    the representative protocols in analysis/sampling_bound.py rather than from a
    measurement. That difference in provenance is why they are named separately here: the
    manuscript must not present them as if they came from the archive.
    """
    import sys
    sys.path.insert(0, str(HERE.parent / "analysis"))
    from sampling_bound import PROTOCOLS, threshold_heart_rate_bpm  # noqa: PLC0415

    wanted = {
        "2026 wide detector, 192 x 0.6, pitch 1.5": "threshold_wide_detector",
        "2026 dual-source high pitch (flash), 3.2": "threshold_dual_source_high_pitch",
    }
    out = {}
    for protocol in PROTOCOLS:
        if protocol.name in wanted:
            window = threshold_heart_rate_bpm(protocol, cycles_needed=2.5)
            out[wanted[protocol.name]] = round(window[0]) if window else None
            out[wanted[protocol.name] + "_speed"] = round(protocol.table_speed_mm_s, 1)
    return out


def cohort_metrics() -> dict:
    """The image cohort, under the criterion frozen in step 5."""
    data = _load("cohort_outcome.json")
    series = data["series"]
    usable = [s for s in series if "technical_failure" not in s]
    recovered = [s for s in usable if s.get("recovered")]
    ceiling = data["criterion"]["predict_recoverable_below_bpm"]

    agree = sum(
        1 for s in usable
        if (s["threshold_bpm_border"] <= ceiling) == bool(s.get("recovered"))
    )
    predicted = [s for s in usable if s["threshold_bpm_border"] <= ceiling]
    return {
        "cohort_series": len(series),
        "cohort_analysed": len(usable),
        "cohort_technical_failures": len(series) - len(usable),
        "cohort_recovered": len(recovered),
        "cohort_predicted_recoverable": len(predicted),
        "cohort_predicted_and_recovered": sum(1 for s in predicted if s.get("recovered")),
        "cohort_agreement": agree,
        "cohort_agreement_percent": round(100 * agree / len(usable)),
        "cohort_pinned": sum(1 for s in usable if s.get("pinned")),
        "prediction_ceiling_bpm": round(ceiling),
    }


def learned_metrics() -> dict:
    """The two training conditions, and the calibration gap between them."""
    data = _load("learned_estimator.json")
    out = {}
    for name, key in (("trained_above_the_bound", "above"),
                      ("trained_across_the_boundary", "across")):
        rows = data["conditions"][name]
        below = [r for r in rows if r["cycles"] < 2.5]
        at_and_above = [r for r in rows if r["cycles"] >= 2.5]
        out[f"{key}_accuracy_below_max_percent"] = round(100 * max(r["accuracy"] for r in below))
        out[f"{key}_calibration_below_min"] = round(min(r["calibration"] for r in below), 2)
        out[f"{key}_calibration_below_max"] = round(max(r["calibration"] for r in below), 2)
        out[f"{key}_reported_sd_below_max"] = round(max(r["median_reported_sd"] for r in below), 3)
        out[f"{key}_accuracy_at_bound_percent"] = round(
            100 * max(r["accuracy"] for r in at_and_above)
        )
    return out


def main() -> int:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    metrics = {}
    for section in (simulation_metrics, header_metrics, representative_protocol_metrics,
                    cohort_metrics, learned_metrics):
        metrics.update(section())

    manifest = {
        "frozen_on": date.today().isoformat(),
        "note": ("Every number the manuscript quotes is resolved from here at build time. "
                 "A quantity absent from this file may not be asserted in the paper."),
        "metrics": metrics,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"{len(metrics)} metrics collected\n")
    for key, value in metrics.items():
        print(f"  {key:44} {value}")
    print(f"\nwritten: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
