"""Compare real border traces with simulated ones, on the four properties named in step 7.

The step-3 sweep says these series should have recovered: sigma was measured at 0.37 to
0.43, N_min at that sigma is 2.5, and the cohort wrote 4 to 11 cycles. Three of seventeen
did. Something structural differs, and the amplitude of the noise is not it.

Nothing here proposes a mechanism. It measures four properties on both populations and
reports where they differ. Whether a difference *causes* the failure is decided in the
second half, by putting it into the simulator and seeing whether the failure reappears.

    python analysis/diagnose_failure.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from extract_border_trace import CACHE, RESULTS, left_border_trace, load_series  # noqa: E402
from joint_period_fit import CORONAL_FRACTIONS  # noqa: E402
from measure_n_min import CENTRAL, simulate  # noqa: E402

SLOWEST_BPM, FASTEST_BPM = 40.0, 120.0


def _quartic_residual(z: np.ndarray, values: np.ndarray):
    span = z[-1] - z[0]
    v = (z - z[0]) / span if span > 0 else z
    design = np.column_stack([np.ones_like(v), v, v**2, v**3, v**4])
    solution, *_ = np.linalg.lstsq(design, values, rcond=None)
    return values - design @ solution


def properties(z: np.ndarray, values: np.ndarray, table_speed: float | None) -> dict:
    """The four candidates from step 7, measured the same way on real and simulated traces."""
    raw_variance = float(np.var(values))
    residual = _quartic_residual(z, values)
    residual_variance = float(np.var(residual))

    step = float(np.median(np.diff(z))) if z.size > 1 else 1.0
    n = residual.size
    window = np.hanning(n)
    spectrum = np.abs(np.fft.rfft(residual * window)) ** 2
    frequency = np.fft.rfftfreq(n, d=step)  # cycles per mm

    # The physiological band, in cycles per mm, from the header's table speed.
    if table_speed:
        low = SLOWEST_BPM / 60.0 / table_speed
        high = FASTEST_BPM / 60.0 / table_speed
    else:
        low, high = frequency[1], frequency[-1]
    band = (frequency >= low) & (frequency <= high)
    total = float(spectrum[1:].sum())
    in_band = float(spectrum[band].sum()) if band.any() else 0.0
    # A flat spectrum would put this fraction of its power in the band; the ratio of the
    # two is what says whether anything is concentrated there.
    expected = float(band.sum()) / max(len(frequency) - 1, 1)

    steps = np.abs(np.diff(values))
    scale = np.std(residual) if np.std(residual) > 0 else 1.0

    # Non-stationarity: amplitude of the first half against the second.
    half = n // 2
    first, second = np.std(residual[:half]), np.std(residual[half:])
    drift = float(max(first, second) / max(min(first, second), 1e-9))

    return {
        "baseline_share": 1.0 - residual_variance / raw_variance if raw_variance > 0 else 0.0,
        "band_power_fraction": in_band / total if total > 0 else 0.0,
        "band_power_enrichment": (in_band / total) / expected if total > 0 and expected > 0 else 0.0,
        "large_steps_per_100": float(100.0 * np.mean(steps > 3 * scale)) if steps.size else 0.0,
        "amplitude_drift_ratio": drift,
    }


def real_traces():
    catalogue = {}
    for name in ("pilot_series.json", "cohort_images.json"):
        path = RESULTS / name
        if path.is_file():
            for record in json.loads(path.read_text(encoding="utf-8")):
                catalogue[record["series_uid"]] = record

    rows = []
    for directory in sorted(CACHE.iterdir()):
        if not directory.is_dir():
            continue
        try:
            volume = load_series(directory)
        except Exception:  # noqa: BLE001
            continue
        speed = volume.table_speed_mm_s
        if not speed:
            continue
        height = volume.array.shape[1]
        for fraction in CORONAL_FRACTIONS:
            trace = left_border_trace(volume, int(height * fraction))
            finite = np.isfinite(trace)
            if finite.sum() < 64:
                continue
            rows.append(properties(volume.z_mm[finite], trace[finite], speed))
        print(f"  {catalogue.get(directory.name, {}).get('patient', directory.name[:14])}: "
              f"{len(rows)} traces so far")
    return rows


def simulated_traces(count: int, cycles_range=(4.0, 11.0), noise=0.40):
    rng = np.random.default_rng(20260907)
    rows = []
    for _ in range(count):
        cycles = float(rng.uniform(*cycles_range))
        trace = simulate(cycles, 32, noise, CENTRAL["baseline"], CENTRAL["variability"], rng)
        # the simulator works in arbitrary units where the period is 1, so the band is
        # expressed against a table speed that makes 60 bpm land on that period
        rows.append(properties(trace.z, trace.b, table_speed=1.0))
    return rows


def summarise(name: str, rows: list[dict]) -> dict:
    keys = rows[0].keys()
    out = {}
    print(f"\n{name}  (n = {len(rows)})")
    print(f"  {'property':26} {'median':>10} {'10th':>10} {'90th':>10}")
    for key in keys:
        values = np.array([r[key] for r in rows])
        median, low, high = (float(np.median(values)), float(np.percentile(values, 10)),
                             float(np.percentile(values, 90)))
        out[key] = {"median": median, "p10": low, "p90": high}
        print(f"  {key:26} {median:10.3f} {low:10.3f} {high:10.3f}")
    return out


def main() -> int:
    print("=== measuring real traces")
    real = real_traces()
    print("\n=== measuring simulated traces at the cohort's cycles and sigma")
    simulated = simulated_traces(len(real))

    summary = {
        "real": summarise("real border traces", real),
        "simulated": summarise("simulated traces (4-11 cycles, sigma 0.40)", simulated),
    }

    print("\n=== where they differ")
    print(f"  {'property':26} {'real':>10} {'simulated':>12} {'ratio':>9}  separated?")
    for key in summary["real"]:
        r, s = summary["real"][key], summary["simulated"][key]
        ratio = r["median"] / s["median"] if s["median"] else float("inf")
        # "separated" means the middle 80 per cent of each population do not overlap
        separated = r["p10"] > s["p90"] or r["p90"] < s["p10"]
        print(f"  {key:26} {r['median']:10.3f} {s['median']:12.3f} {ratio:9.2f}  "
              f"{'YES' if separated else 'no'}")

    (RESULTS / "failure_diagnosis.json").write_text(
        json.dumps({"n_real": len(real), "n_simulated": len(simulated), **summary}, indent=2),
        encoding="utf-8",
    )
    print(f"\nwritten: {RESULTS / 'failure_diagnosis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
