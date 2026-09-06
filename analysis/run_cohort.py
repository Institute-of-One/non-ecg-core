"""Test the bound's prediction against the cohort, under the criterion frozen in step 5.

The prediction comes from the header alone; the outcome from the images. Both were defined
before either was computed on anything beyond the three pilots. The primary result is their
**agreement**, not the recovery rate: a high recovery rate unrelated to table speed would
mean the estimator is fitting anatomy, which is the failure most easily mistaken for
success.

    python analysis/run_cohort.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from extract_border_trace import CACHE, RESULTS, left_border_trace, load_series  # noqa: E402
from joint_period_fit import (  # noqa: E402
    CORONAL_FRACTIONS,
    joint_fit,
    leave_one_out,
)

# --------------------------------------------------------------- the frozen criterion

N_MIN = 2.5
PREDICT_RECOVERABLE_BELOW_BPM = 100.0
MAX_LEAVE_ONE_OUT_SPREAD_BPM = 10.0
MAX_MEDIAN_SIGMA = 1.0
MIN_LEVELS = 3

#: Reported alongside the headline so the two calibrated conventions stay visible.
PREDICTION_CEILINGS = (80.0, 100.0, 120.0)
SPREAD_THRESHOLDS = (5.0, 10.0, 20.0)


def threshold_bpm(table_speed: float, extent_mm: float, n_min: float = N_MIN) -> float:
    return 60.0 * table_speed * n_min / extent_mm


def analyse_series(directory: Path) -> dict:
    volume = load_series(directory)
    speed = volume.table_speed_mm_s
    if not speed:
        return {"technical_failure": "no table speed in the header"}

    height = volume.array.shape[1]
    traces = []
    for fraction in CORONAL_FRACTIONS:
        trace = left_border_trace(volume, int(height * fraction))
        finite = np.isfinite(trace)
        if finite.sum() >= 64:
            traces.append((volume.z_mm[finite], trace[finite]))
    if len(traces) < MIN_LEVELS:
        return {"technical_failure": f"only {len(traces)} usable coronal levels"}

    fit = joint_fit(traces, speed)
    dropped = leave_one_out(traces, speed)
    spread = (max(dropped) - min(dropped)) if len(dropped) >= 2 else float("inf")
    span = float(volume.z_mm[-1] - volume.z_mm[0])
    cycles = span / fit["period_mm"]
    sigmas = sorted(level["sigma"] for level in fit["levels"])
    median_sigma = sigmas[len(sigmas) // 2]

    reasons = []
    if fit["pinned_at_band_edge"]:
        reasons.append("pinned at the band edge")
    if cycles < N_MIN:
        reasons.append(f"only {cycles:.1f} cycles written")
    if spread > MAX_LEAVE_ONE_OUT_SPREAD_BPM:
        reasons.append(f"leave-one-out spread {spread:.0f} bpm")
    if median_sigma >= MAX_MEDIAN_SIGMA:
        reasons.append(f"median sigma {median_sigma:.2f}")

    return {
        "table_speed_mm_s": speed,
        "z_span_mm": span,
        "levels": len(traces),
        "period_mm": fit["period_mm"],
        "heart_rate_bpm": fit["heart_rate_bpm"],
        "cycles_written": cycles,
        "leave_one_out_bpm": dropped,
        "leave_one_out_spread_bpm": spread,
        "median_sigma": median_sigma,
        "pinned": fit["pinned_at_band_edge"],
        "recovered": not reasons,
        "why_not": reasons,
        # the prediction, from the header alone, at the cardiac border and at the extent
        # actually analysed
        "threshold_bpm_border": threshold_bpm(speed, 120.0),
        "threshold_bpm_analysed": threshold_bpm(speed, span),
    }


def main() -> int:
    catalogue = {}
    for name in ("pilot_series.json", "cohort_images.json"):
        path = RESULTS / name
        if path.is_file():
            for record in json.loads(path.read_text(encoding="utf-8")):
                catalogue[record["series_uid"]] = record

    results = []
    for directory in sorted(CACHE.iterdir()):
        if not directory.is_dir():
            continue
        record = catalogue.get(directory.name, {})
        try:
            outcome = analyse_series(directory)
        except Exception as error:  # noqa: BLE001 - visible, and counted separately
            outcome = {"technical_failure": repr(error)}
        outcome.update({
            "collection": record.get("collection", "?"),
            "patient": record.get("patient", directory.name[:16]),
            "series_uid": directory.name,
        })
        results.append(outcome)

    usable = [r for r in results if "technical_failure" not in r]
    technical = [r for r in results if "technical_failure" in r]

    print(f"{len(results)} series, {len(usable)} analysed, {len(technical)} technical failures\n")
    header = (f"{'collection':20} {'patient':<18} {'S':>6} {'thr':>5} {'pred':>5} "
              f"{'bpm':>5} {'cyc':>5} {'spread':>7} {'sig':>5}  outcome")
    print(header)
    for r in sorted(usable, key=lambda x: x["table_speed_mm_s"]):
        predicted = r["threshold_bpm_border"] <= PREDICT_RECOVERABLE_BELOW_BPM
        mark = "yes" if r["recovered"] else "no"
        print(f"{r['collection'][:19]:20} {str(r['patient'])[:17]:<18} "
              f"{r['table_speed_mm_s']:6.1f} {r['threshold_bpm_border']:5.0f} "
              f"{('yes' if predicted else 'no'):>5} {r['heart_rate_bpm']:5.0f} "
              f"{r['cycles_written']:5.1f} {r['leave_one_out_spread_bpm']:7.1f} "
              f"{r['median_sigma']:5.2f}  {mark}"
              + ("" if r["recovered"] else "  (" + "; ".join(r["why_not"]) + ")"))
    for r in technical:
        print(f"{r['collection'][:19]:20} {str(r['patient'])[:17]:<18} "
              f"technical failure: {r['technical_failure'][:60]}")

    print("\n=== primary outcome: agreement between prediction and result")
    for ceiling in PREDICTION_CEILINGS:
        table = {"a": 0, "b": 0, "c": 0, "d": 0}
        for r in usable:
            predicted = r["threshold_bpm_border"] <= ceiling
            got = r["recovered"]
            key = "a" if (predicted and got) else "b" if (predicted and not got) \
                else "c" if (not predicted and got) else "d"
            table[key] += 1
        total = sum(table.values())
        agree = table["a"] + table["d"]
        star = "  <- headline" if ceiling == PREDICT_RECOVERABLE_BELOW_BPM else ""
        print(f"  predicted recoverable at <= {ceiling:.0f} bpm: "
              f"agreement {agree}/{total} ({agree / total:.0%})   "
              f"[predicted+recovered {table['a']}, predicted+failed {table['b']}, "
              f"unpredicted+recovered {table['c']}, unpredicted+failed {table['d']}]{star}")

    print("\n=== sensitivity to the calibrated stability threshold")
    for spread_limit in SPREAD_THRESHOLDS:
        recovered = [
            r for r in usable
            if not r["pinned"] and r["cycles_written"] >= N_MIN
            and r["leave_one_out_spread_bpm"] <= spread_limit
            and r["median_sigma"] < MAX_MEDIAN_SIGMA
        ]
        agree = sum(
            1 for r in usable
            if (r["threshold_bpm_border"] <= PREDICT_RECOVERABLE_BELOW_BPM) == (r in recovered)
        )
        print(f"  spread <= {spread_limit:4.0f} bpm: recovered {len(recovered)}/{len(usable)}, "
              f"agreement {agree}/{len(usable)} ({agree / len(usable):.0%})")

    (RESULTS / "cohort_outcome.json").write_text(
        json.dumps({"criterion": {
            "n_min": N_MIN,
            "predict_recoverable_below_bpm": PREDICT_RECOVERABLE_BELOW_BPM,
            "max_leave_one_out_spread_bpm": MAX_LEAVE_ONE_OUT_SPREAD_BPM,
            "max_median_sigma": MAX_MEDIAN_SIGMA,
        }, "series": results}, indent=2),
        encoding="utf-8",
    )
    print(f"\nwritten: {RESULTS / 'cohort_outcome.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
