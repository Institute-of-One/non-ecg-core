"""How deep is the minimum the cohort criterion was accepting?

The frozen criterion asks whether the fitted period is stable when a level is dropped. It
never asks whether the cost surface has a minimum worth finding. On the one series whose
true rate is known, the global minimum is only about eight per cent below the median cost
across the whole physiological band, the true period is not even a local minimum, and the
six levels individually prefer rates from 40 to 98 bpm. The joint fit still returned a
figure that survived leave-one-out.

If that is general, it explains the cohort outcome without any of the four candidates tested
in step 7: there is no periodic signal to find, a flat objective makes the argmin arbitrary,
and an arbitrary argmin is stable under leave-one-out precisely because nothing pins it.

This is a post-hoc diagnosis added 2026-09-29. It does not alter the frozen cohort outcome;
it measures a quantity that outcome never recorded.

    python analysis/diagnose_flatness.py
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
    FASTEST_BPM,
    SLOWEST_BPM,
    _level_cost,
)

OUT = RESULTS / "flatness.json"


def diagnose(directory: Path) -> dict:
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
            traces.append((fraction, volume.z_mm[finite], trace[finite]))
    if len(traces) < 3:
        return {"technical_failure": f"only {len(traces)} usable coronal levels"}

    grid = np.linspace(speed * 60.0 / FASTEST_BPM, speed * 60.0 / SLOWEST_BPM, 600)
    weights = [1.0 / max(float(np.var(values)), 1e-9) for _, _, values in traces]
    costs = np.array([
        sum(weight * _level_cost(z, values, period)[0]
            for weight, (_, z, values) in zip(weights, traces))
        for period in grid
    ])
    best = int(np.argmin(costs))

    preferred = []
    for _, z, values in traces:
        level_costs = np.array([_level_cost(z, values, p)[0] for p in grid])
        preferred.append(60.0 * speed / grid[int(np.argmin(level_costs))])

    return {
        "table_speed_mm_s": speed,
        "levels": len(traces),
        "fitted_bpm": float(60.0 * speed / grid[best]),
        # 1.00 means the best period fits no better than a typical one.
        "median_over_min": float(np.median(costs) / costs[best]),
        "max_over_min": float(np.max(costs) / costs[best]),
        "level_preferred_bpm": [float(p) for p in preferred],
        "level_preferred_spread_bpm": float(max(preferred) - min(preferred)),
    }


def main() -> int:
    directories = sorted(p for p in CACHE.iterdir() if p.is_dir())
    if not directories:
        raise SystemExit(f"no cached series under {CACHE}")

    rows = []
    for index, directory in enumerate(directories, 1):
        result = diagnose(directory)
        result["series_uid"] = directory.name
        rows.append(result)
        if "technical_failure" in result:
            print(f"[{index:2d}/{len(directories)}] {directory.name[-10:]}  "
                  f"FAILED {result['technical_failure']}", flush=True)
        else:
            print(f"[{index:2d}/{len(directories)}] {directory.name[-10:]}  "
                  f"fit {result['fitted_bpm']:6.1f} bpm  depth {result['median_over_min']:.3f}  "
                  f"levels prefer spread {result['level_preferred_spread_bpm']:5.1f} bpm",
                  flush=True)

    if len(rows) != len(directories):
        raise SystemExit("a series produced no row; a silent drop would look like a result")

    analysed = [r for r in rows if "technical_failure" not in r]
    depths = sorted(r["median_over_min"] for r in analysed)
    summary = {
        "checked_on": "2026-09-29",
        "series_checked": len(rows),
        "series_analysed": len(analysed),
        "depth_min": depths[0],
        "depth_median": depths[len(depths) // 2],
        "depth_max": depths[-1],
        "series": rows,
    }
    OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nanalysed {len(analysed)} of {len(rows)}")
    print(f"depth of the minimum (median cost / best cost): "
          f"min {depths[0]:.3f}, median {summary['depth_median']:.3f}, max {depths[-1]:.3f}")
    print(f"\nwritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
