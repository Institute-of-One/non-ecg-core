"""Did the fitter fail to find the true period, or does the trace not contain it?

The reference case returned 67.4 bpm against a recorded 75. Those are two different
defects with two different consequences. If the cost at the true period is lower than at the
period returned, the search missed it and the search is broken. If the cost at the true
period is higher, the trace genuinely prefers a period that is not the heart's, and the
failure is a property of the signal rather than of the optimiser.

This is a diagnosis. It does not alter the frozen result in results/reference_case.json, and
the outcome reported in the paper remains the one the frozen pipeline produced.

    python analysis/tcia_search/diagnose_reference_case.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "analysis"))

from extract_border_trace import left_border_trace, load_series      # noqa: E402
from joint_period_fit import (                                       # noqa: E402
    CORONAL_FRACTIONS,
    FASTEST_BPM,
    SLOWEST_BPM,
    _level_cost,
)

SERIES_UID = "1.3.6.1.4.1.14519.5.2.1.264532322608206684963835753501167761257"
REFERENCE_BPM = 75.0
RECORDED_RANGE_BPM = (72.0, 78.0)
OUT = REPO / "results" / "reference_case_diagnosis.json"


def local_minima(costs: np.ndarray) -> list[int]:
    return [i for i in range(1, len(costs) - 1)
            if costs[i] < costs[i - 1] and costs[i] < costs[i + 1]]


def main() -> int:
    volume = load_series(REPO / "data_cache" / SERIES_UID)
    speed = volume.table_speed_mm_s
    height = volume.array.shape[1]

    traces = []
    for fraction in CORONAL_FRACTIONS:
        trace = left_border_trace(volume, int(height * fraction))
        finite = np.isfinite(trace)
        if finite.sum() >= 64:
            traces.append((fraction, volume.z_mm[finite], trace[finite]))

    grid = np.linspace(speed * 60.0 / FASTEST_BPM, speed * 60.0 / SLOWEST_BPM, 600)
    weights = [1.0 / max(float(np.var(values)), 1e-9) for _, _, values in traces]
    costs = np.array([
        sum(weight * _level_cost(z, values, period)[0]
            for weight, (_, z, values) in zip(weights, traces))
        for period in grid
    ])

    true_period = speed * 60.0 / REFERENCE_BPM
    fitted_index = int(np.argmin(costs))
    true_index = int(np.argmin(np.abs(grid - true_period)))
    minima = local_minima(costs)

    per_level = []
    for (fraction, z, values), weight in zip(traces, weights):
        level_costs = np.array([_level_cost(z, values, p)[0] for p in grid])
        best = int(np.argmin(level_costs))
        _, peak_to_peak, _, residual_sd = _level_cost(z, values, grid[best])
        per_level.append({
            "coronal_fraction": fraction,
            "preferred_period_mm": float(grid[best]),
            "preferred_bpm": float(60.0 * speed / grid[best]),
            "cost_at_true_over_best": float(level_costs[true_index] / level_costs[best]),
            "sigma_at_preferred": float(residual_sd / peak_to_peak) if peak_to_peak else None,
            "cycles_spanned": float((z[-1] - z[0]) / grid[best]),
        })

    result = {
        "series_uid": SERIES_UID,
        "table_speed_mm_s": speed,
        "search_band_mm": [float(grid[0]), float(grid[-1])],
        "grid_step_mm": float(grid[1] - grid[0]),
        "true_period_mm": true_period,
        "true_period_in_band": bool(grid[0] <= true_period <= grid[-1]),
        "fitted_period_mm": float(grid[fitted_index]),
        "fitted_bpm": float(60.0 * speed / grid[fitted_index]),
        "cost_at_fitted": float(costs[fitted_index]),
        "cost_at_true": float(costs[true_index]),
        "cost_at_true_over_fitted": float(costs[true_index] / costs[fitted_index]),
        "cost_median_over_fitted": float(np.median(costs) / costs[fitted_index]),
        "true_period_is_local_minimum": bool(true_index in minima),
        "local_minima_bpm": [float(60.0 * speed / grid[i]) for i in minima],
        "local_minima_cost_over_fitted": [float(costs[i] / costs[fitted_index]) for i in minima],
        # The curve itself, so the figure is drawn from the run rather than recomputed
        # from a volume the reader may not have downloaded.
        "cost_curve": {
            "bpm": [float(60.0 * speed / p) for p in grid],
            "cost_over_fitted": [float(c / costs[fitted_index]) for c in costs],
        },
        "per_level": per_level,
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"search band        : {grid[0]:.1f} - {grid[-1]:.1f} mm, step {grid[1]-grid[0]:.3f}")
    print(f"true period        : {true_period:.1f} mm ({REFERENCE_BPM} bpm) "
          f"{'IN band' if result['true_period_in_band'] else 'OUTSIDE band'}")
    print(f"fitted period      : {grid[fitted_index]:.1f} mm ({result['fitted_bpm']:.1f} bpm)")
    print()
    print(f"cost at true / at fitted : {result['cost_at_true_over_fitted']:.4f}"
          f"   ({'TRUE IS BETTER -> search defect' if result['cost_at_true_over_fitted'] < 1
              else 'trace prefers the fitted period -> not a search defect'})")
    print(f"cost at median / fitted  : {result['cost_median_over_fitted']:.4f}")
    print(f"true period is a local minimum: {result['true_period_is_local_minimum']}")
    print(f"local minima (bpm) : {[round(b, 1) for b in result['local_minima_bpm']]}")
    print()
    print("per level:")
    for level in per_level:
        print(f"  row {level['coronal_fraction']:.2f}: prefers "
              f"{level['preferred_bpm']:6.1f} bpm  "
              f"cost(true)/cost(best) = {level['cost_at_true_over_best']:.3f}  "
              f"sigma {level['sigma_at_preferred']:.3f}  "
              f"cycles {level['cycles_spanned']:.2f}")
    print(f"\nwritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
