"""Is the tracked border where the mediastinum is, or somewhere else entirely?

The extraction takes the left edge of the soft-tissue run that crosses the midline of a
coronal row. In a chest CT that edge is the left mediastinal border, because the lung
separates the chest wall from the mediastinum and breaks the run. Where there is no lung —
below the diaphragm, or in a patient whose arms are down — the run starts at the skin, and
the method returns the body surface while reporting nothing unusual.

Nothing in the pipeline noticed this. The fit, the leave-one-out test and the residual
criterion all behave the same way on a trace of the patient's outline as on a trace of the
cardiac border. It was found by drawing the trace on the image, which no automatic check did.

This measures, for every cached series, where the tracked border sits across the image. A
border at a few per cent of the image width is the skin; one near the middle is the
mediastinum.

    python analysis/check_border_position.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from extract_border_trace import CACHE, RESULTS, left_border_trace, load_series  # noqa: E402
from joint_period_fit import CORONAL_FRACTIONS                                   # noqa: E402

OUT = RESULTS / "border_position.json"

#: A border closer to the edge than this is not the mediastinum. The mediastinum sits near
#: the middle of a coronal image; the skin sits at the edge. The threshold is loose on
#: purpose, because the two cases are an order of magnitude apart rather than adjacent.
SURFACE_FRACTION = 0.10


def measure(directory: Path) -> dict:
    volume = load_series(directory)
    width_mm = volume.array.shape[2] * volume.spacing_xy_mm[1]
    levels = []
    for fraction in CORONAL_FRACTIONS:
        trace = left_border_trace(volume, int(volume.array.shape[1] * fraction))
        finite = np.isfinite(trace)
        if finite.sum() < 64:
            continue
        values = trace[finite]
        levels.append({
            "coronal_fraction": fraction,
            "median_fraction_of_width": float(np.median(values) / width_mm),
            "share_within_surface": float(np.mean(values < SURFACE_FRACTION * width_mm)),
        })
    if not levels:
        return {"series_uid": directory.name, "technical_failure": "no usable level"}
    medians = [level["median_fraction_of_width"] for level in levels]
    return {
        "series_uid": directory.name,
        "image_width_mm": round(width_mm),
        "z_span_mm": round(float(volume.z_mm[-1] - volume.z_mm[0])),
        "levels": levels,
        "median_fraction_of_width": float(np.median(medians)),
        "share_of_levels_at_the_surface": float(
            np.mean([level["share_within_surface"] > 0.5 for level in levels])),
    }


def main() -> int:
    directories = sorted(p for p in CACHE.iterdir() if p.is_dir())
    if not directories:
        raise SystemExit(f"no cached series under {CACHE}")

    rows = []
    for index, directory in enumerate(directories, 1):
        row = measure(directory)
        rows.append(row)
        if "technical_failure" in row:
            print(f"[{index:2d}/{len(directories)}] {directory.name[-10:]}  "
                  f"FAILED {row['technical_failure']}", flush=True)
        else:
            print(f"[{index:2d}/{len(directories)}] {directory.name[-10:]}  "
                  f"border at {row['median_fraction_of_width']:5.1%} of width  "
                  f"levels at the surface: {row['share_of_levels_at_the_surface']:4.0%}",
                  flush=True)

    if len(rows) != len(directories):
        raise SystemExit("a series produced no row")

    measured = [r for r in rows if "technical_failure" not in r]
    at_surface = [r for r in measured if r["share_of_levels_at_the_surface"] > 0.5]
    OUT.write_text(json.dumps({
        "checked_on": "2026-09-29",
        "surface_fraction": SURFACE_FRACTION,
        "series_checked": len(rows),
        "series_tracking_the_surface": len(at_surface),
        "series_tracking_the_surface_uids": [r["series_uid"] for r in at_surface],
        "series": rows,
    }, indent=2), encoding="utf-8")
    print(f"\nseries checked: {len(rows)} | tracking the body surface rather than the "
          f"mediastinum: {len(at_surface)}")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
