"""Fit one period across every coronal level at once, because there is only one heart.

Six independent fits to six coronal levels threw away the strongest constraint available.
The levels differ in which structure the border follows -- heart at some rows, descending
aorta at others -- so their amplitudes differ and their phases differ, but **the period is
common to all of them**, and for two reasons that are worth separating.

The first is trivial: one heart, one rate.

The second is about the acquisition, and it is the reason the levels can be tied together
so tightly. In a helical scan the time coordinate is a function of z alone. Every coronal
level shares that z axis, so pixels at the same z were acquired at the same moment whatever
row they sit in. The time mapping is not merely similar across levels, it is identical.

What does vary within a slice is azimuth: a slice is reconstructed from about half a
rotation, so structures at different angles are effectively sampled at slightly different
moments -- 0.14 s on a 0.29 s rotation, which is 14 per cent of a cardiac cycle at 60 bpm.
That is a fixed offset per structure, not a scatter, and the per-level phase absorbs it.
The absorbed offset is not a nuisance either: a phase gradient down the descending aorta is
pulse transit.

    python analysis/joint_period_fit.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from extract_border_trace import (  # noqa: E402
    CACHE,
    RESULTS,
    left_border_trace,
    load_series,
)

#: Physiological bounds. The band is set by these and by the header's table speed, never by
#: what the data prefers.
SLOWEST_BPM = 40.0
FASTEST_BPM = 120.0

#: A fit spanning fewer cycles than this is not a period measurement, whatever it returns.
#: This is N_min from step 3, used here as the rejection rule it always implied.
MIN_CYCLES = 2.5

CORONAL_FRACTIONS = (0.45, 0.50, 0.55, 0.60, 0.65, 0.70)


def _level_cost(z: np.ndarray, values: np.ndarray, period: float):
    """Residual for one level at a given period, with baseline, amplitude and phase solved.

    Returns the residual sum of squares, the peak-to-peak amplitude and the phase, the last
    of which is what carries the azimuthal offset and, along the aorta, pulse transit.
    """
    span = z[-1] - z[0]
    v = (z - z[0]) / span
    u = (z - z[0]) / period
    design = np.column_stack([
        np.cos(2 * np.pi * u), np.sin(2 * np.pi * u),
        np.ones_like(v), v, v**2, v**3, v**4,
    ])
    solution, *_ = np.linalg.lstsq(design, values, rcond=None)
    residual = values - design @ solution
    amplitude = float(np.hypot(solution[0], solution[1]))
    phase = float(np.arctan2(-solution[1], solution[0]))
    return float(np.sum(residual**2)), 2 * amplitude, phase, float(np.std(residual))


def joint_fit(traces: list[tuple[np.ndarray, np.ndarray]], speed: float):
    """One period for all levels; amplitude and phase free per level."""
    shortest = speed * 60.0 / FASTEST_BPM
    longest = speed * 60.0 / SLOWEST_BPM
    grid = np.linspace(shortest, longest, 600)

    # Each level contributes its residual normalised by its own variance, so a level with a
    # large anatomical swing does not simply outvote the others.
    weights = [1.0 / max(float(np.var(values)), 1e-9) for _, values in traces]

    costs = np.array([
        sum(weight * _level_cost(z, values, period)[0]
            for weight, (z, values) in zip(weights, traces))
        for period in grid
    ])
    best = int(np.argmin(costs))
    period = float(grid[best])

    #: Pinning at either end of the physiological band means the fit wanted to leave it,
    #: which is the signature of no periodic signal rather than of a very fast or very
    #: slow heart.
    pinned = best <= 2 or best >= len(grid) - 3

    levels = []
    for z, values in traces:
        _, peak_to_peak, phase, residual_sd = _level_cost(z, values, period)
        levels.append({
            "peak_to_peak_mm": peak_to_peak,
            "phase_rad": phase,
            "residual_sd_mm": residual_sd,
            "sigma": residual_sd / peak_to_peak if peak_to_peak > 0 else float("inf"),
            "cycles": float((z[-1] - z[0]) / period),
        })
    return {
        "period_mm": period,
        "pinned_at_band_edge": pinned,
        "heart_rate_bpm": 60.0 * speed / period,
        "levels": levels,
        "cost_curve_min": float(costs[best]),
        "cost_curve_median": float(np.median(costs)),
    }


def leave_one_out(traces, speed: float) -> list[float]:
    """Refit with each level dropped in turn: the stability the six independent fits lacked."""
    rates = []
    for index in range(len(traces)):
        remaining = [t for position, t in enumerate(traces) if position != index]
        if len(remaining) < 2:
            continue
        rates.append(joint_fit(remaining, speed)["heart_rate_bpm"])
    return rates


def main() -> int:
    catalogue = json.loads((RESULTS / "pilot_series.json").read_text(encoding="utf-8"))
    everything = []

    for record in catalogue:
        directory = CACHE / record["series_uid"]
        if not directory.is_dir():
            continue
        volume = load_series(directory)
        speed = volume.table_speed_mm_s
        if not speed:
            continue
        height = volume.array.shape[1]

        traces = []
        for fraction in CORONAL_FRACTIONS:
            trace = left_border_trace(volume, int(height * fraction))
            finite = np.isfinite(trace)
            if finite.sum() >= 64:
                traces.append((volume.z_mm[finite], trace[finite]))
        if len(traces) < 3:
            print(f"{record['collection']}: only {len(traces)} usable levels, skipped")
            continue

        fit = joint_fit(traces, speed)
        dropped = leave_one_out(traces, speed)
        span = float(volume.z_mm[-1] - volume.z_mm[0])
        cycles = span / fit["period_mm"]

        verdict = "no periodic signal (fit pinned at the band edge)" if fit["pinned_at_band_edge"] \
            else ("too few cycles written" if cycles < MIN_CYCLES else "period recovered")

        print(f"\n=== {record['collection']} / {record['patient']}")
        print(f"    S = {speed:.1f} mm/s, threshold {60 * speed * MIN_CYCLES / 120:.0f} bpm "
              f"at the cardiac border")
        print(f"    levels used: {len(traces)}, scanned {span:.0f} mm")
        print(f"    joint period {fit['period_mm']:.1f} mm  ->  "
              f"{fit['heart_rate_bpm']:.0f} bpm, {cycles:.1f} cycles written")
        if dropped:
            print(f"    leave-one-level-out: {min(dropped):.0f}-{max(dropped):.0f} bpm "
                  f"(spread {max(dropped) - min(dropped):.0f})")
        sigmas = sorted(level["sigma"] for level in fit["levels"])
        print(f"    sigma across levels: {sigmas[0]:.2f} to {sigmas[-1]:.2f}, "
              f"median {sigmas[len(sigmas) // 2]:.2f}")
        print(f"    verdict: {verdict}")

        everything.append({
            "collection": record["collection"],
            "patient": record["patient"],
            "series_uid": record["series_uid"],
            "table_speed_mm_s": speed,
            "z_span_mm": span,
            "cycles_written": cycles,
            "leave_one_out_bpm": dropped,
            "verdict": verdict,
            **fit,
        })

    destination = RESULTS / "joint_period.json"
    destination.write_text(json.dumps(everything, indent=2), encoding="utf-8")
    print(f"\nwritten: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
