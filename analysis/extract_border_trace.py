"""Measure the cardiac border trace in a real scan, and with it the noise the bound needs.

The signal is the one the 2003 observation was about: in a coronal reformat the left
mediastinal silhouette is wavy, because the table advanced while the heart beat. Below the
heart the same silhouette continues as the descending aorta against the left lung, which is
the longer structure the budget identity says is needed.

The lung-to-soft-tissue step is about 800 HU, so this border is located far more precisely
than a contrast-filled chamber edge would be. That is why it, and not the endocardium, is
what the estimator reads.

**Every coronal level is reported, not the best one.** Choosing the plane that shows the
clearest wave and presenting that is how a figure stops being evidence, and a reviewer of
the 2003 manuscript said as much about its figures coming from different patients.

    python analysis/extract_border_trace.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pydicom

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / "data_cache"
RESULTS = HERE.parent / "results"

#: Lung reads about -800 HU and mediastinum about +40, so the step is enormous and the
#: threshold sits far from either. Nothing here is sensitive to its exact value.
LUNG_THRESHOLD_HU = -300.0

#: A mediastinal run must be at least this wide to be the mediastinum rather than a vessel
#: crossing the lung field.
MIN_MEDIASTINUM_MM = 25.0


@dataclass
class Volume:
    array: np.ndarray  # (z, y, x) in Hounsfield units
    z_mm: np.ndarray   # slice positions, ascending
    spacing_xy_mm: tuple[float, float]
    table_speed_mm_s: float | None
    series_uid: str
    patient: str


def load_series(directory: Path) -> Volume:
    """Read a cached series into a volume, sorted by true slice position."""
    slices = []
    for path in sorted(directory.iterdir()):
        try:
            dataset = pydicom.dcmread(path)
        except Exception:  # noqa: BLE001 - a non-DICOM file in the cache is skipped
            continue
        if not hasattr(dataset, "pixel_array") or not hasattr(dataset, "ImagePositionPatient"):
            continue
        slices.append(dataset)
    if not slices:
        raise RuntimeError(f"no readable slices in {directory}")

    slices.sort(key=lambda dataset: float(dataset.ImagePositionPatient[2]))
    first = slices[0]
    slope = float(getattr(first, "RescaleSlope", 1) or 1)
    intercept = float(getattr(first, "RescaleIntercept", 0) or 0)
    array = np.stack([s.pixel_array.astype(np.float32) for s in slices]) * slope + intercept
    z = np.array([float(s.ImagePositionPatient[2]) for s in slices])

    speed = getattr(first, "TableSpeed", None)
    if speed is None:
        pitch = getattr(first, "SpiralPitchFactor", None)
        rotation = getattr(first, "RevolutionTime", None)
        collimation = getattr(first, "TotalCollimationWidth", None)
        if None not in (pitch, rotation, collimation):
            speed = float(pitch) * float(collimation) / float(rotation)
    row_mm, column_mm = (float(v) for v in first.PixelSpacing)

    return Volume(
        array=array,
        z_mm=z,
        spacing_xy_mm=(row_mm, column_mm),
        table_speed_mm_s=float(speed) if speed is not None else None,
        series_uid=str(first.SeriesInstanceUID),
        patient=str(getattr(first, "PatientID", "?")),
    )


def left_border_trace(volume: Volume, coronal_row: int) -> np.ndarray:
    """The left edge of the mediastinal silhouette, in millimetres, for each slice.

    Tracked with a continuity constraint rather than chosen independently per slice. The
    first version took the widest soft-tissue run crossing the midline at each slice on its
    own, and it jumped between the aorta, the heart, the hilum and the chest wall: the
    border swung 168 mm over the scan with twenty jumps larger than 5 mm, while the median
    slice-to-slice change was 0.00 mm. The signal was there and a handful of catastrophic
    jumps were sitting on top of it.

    So the border is followed: each slice takes the candidate closest to where the border
    was on the last one, and a slice with no candidate within reach is left empty rather
    than filled with the nearest available structure.
    """
    _, column_mm = volume.spacing_xy_mm
    minimum_run = int(MIN_MEDIASTINUM_MM / column_mm)
    jump_limit_mm = 6.0
    coronal = volume.array[:, coronal_row, :]
    trace = np.full(coronal.shape[0], np.nan)

    def candidates(row: np.ndarray) -> list[float]:
        solid = row > LUNG_THRESHOLD_HU
        if not solid.any():
            return []
        edges = np.diff(solid.astype(np.int8))
        starts = list(np.flatnonzero(edges == 1) + 1)
        ends = list(np.flatnonzero(edges == -1) + 1)
        if solid[0]:
            starts.insert(0, 0)
        if solid[-1]:
            ends.append(solid.size)
        middle = solid.size // 2
        return [
            start * column_mm
            for start, end in zip(starts, ends)
            if end - start >= minimum_run and start <= middle <= end
        ]

    # Start in the middle of the scan, where the mediastinum is widest and least ambiguous,
    # and track outwards in both directions.
    order = list(range(coronal.shape[0] // 2, coronal.shape[0])) +         list(range(coronal.shape[0] // 2 - 1, -1, -1))
    previous = None
    for count, index in enumerate(order):
        options = candidates(coronal[index])
        if not options:
            continue
        if count == len(order) - coronal.shape[0] // 2:
            previous = None  # restarting the downward pass from the middle
        if previous is None:
            chosen = max(options)
        else:
            nearest = min(options, key=lambda value: abs(value - previous))
            if abs(nearest - previous) > jump_limit_mm:
                continue
            chosen = nearest
        trace[index] = chosen
        previous = chosen

    return trace


def fit_period(z_mm: np.ndarray, trace: np.ndarray, period_grid: np.ndarray):
    """Fit baseline plus one harmonic; return the best period and the residual fraction.

    The estimator is the `fundamental` one from step 3 -- it assumes the border repeats and
    nothing about the shape of the repetition -- so the noise it leaves is the noise the
    step-3 sweep was parameterised by.
    """
    finite = np.isfinite(trace)
    if finite.sum() < 32:
        return None
    z = z_mm[finite]
    values = trace[finite]
    span = z[-1] - z[0]
    v = (z - z[0]) / span

    best = None
    for period in period_grid:
        u = (z - z[0]) / period
        # A quartic baseline. The anatomical envelope varies on scales of 100 mm and more
        # while the band being searched is 17 to 80 mm, so this is flexible enough to
        # absorb anatomy and far too stiff to imitate the oscillation being looked for.
        design = np.column_stack([
            np.cos(2 * np.pi * u), np.sin(2 * np.pi * u),
            np.ones_like(v), v, v**2, v**3, v**4,
        ])
        solution, *_ = np.linalg.lstsq(design, values, rcond=None)
        residual = values - design @ solution
        cost = float(np.sum(residual**2))
        if best is None or cost < best[1]:
            amplitude = float(np.hypot(solution[0], solution[1]))
            best = (float(period), cost, amplitude, float(np.std(residual)))

    period, _, amplitude, residual_sd = best
    peak_to_peak = 2 * amplitude
    return {
        "period_mm": period,
        "pulsation_peak_to_peak_mm": peak_to_peak,
        "residual_sd_mm": residual_sd,
        # sigma as step 3 defines it: residual against the pulsation it sits on
        "sigma": residual_sd / peak_to_peak if peak_to_peak > 0 else float("inf"),
        "samples": int(finite.sum()),
        "z_span_mm": float(span),
    }


def analyse(directory: Path) -> dict:
    volume = load_series(directory)
    height = volume.array.shape[1]
    # Posterior half only: the descending aorta and the cardiac border live there, and
    # sweeping the whole volume would mostly report sternum and spine.
    levels = [int(height * fraction) for fraction in (0.45, 0.50, 0.55, 0.60, 0.65, 0.70)]

    span = float(volume.z_mm[-1] - volume.z_mm[0])
    # The period band is fixed by physiology and by the table speed in the header, not by
    # what the data prefers: W = S x 60 / rate, over 40 to 120 bpm. The first version
    # searched up to half the scanned length and the anatomical envelope won every time,
    # pinning the fit at 156 and 249 mm and implying heart rates of 13 to 38 bpm.
    speed = volume.table_speed_mm_s or 0.0
    shortest = speed * 60.0 / 120.0
    longest = speed * 60.0 / 40.0
    grid = np.linspace(shortest, longest, 300)

    findings = []
    for level in levels:
        trace = left_border_trace(volume, level)
        fit = fit_period(volume.z_mm, trace, grid)
        if fit is None:
            findings.append({"coronal_row": level, "usable": False})
            continue
        heart_rate = None
        if volume.table_speed_mm_s:
            heart_rate = 60.0 * volume.table_speed_mm_s / fit["period_mm"]
        findings.append({
            "coronal_row": level,
            "usable": True,
            "cycles_written": fit["z_span_mm"] / fit["period_mm"],
            "implied_heart_rate_bpm": heart_rate,
            **fit,
        })

    return {
        "patient": volume.patient,
        "series_uid": volume.series_uid,
        "table_speed_mm_s": volume.table_speed_mm_s,
        "slices": int(volume.array.shape[0]),
        "z_span_mm": span,
        "levels": findings,
    }


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    if not CACHE.is_dir():
        print("nothing cached; run data/fetch_pilot.py first")
        return 1

    catalogue = json.loads((RESULTS / "pilot_series.json").read_text(encoding="utf-8"))
    by_uid = {record["series_uid"]: record for record in catalogue}

    everything = []
    for directory in sorted(CACHE.iterdir()):
        if not directory.is_dir():
            continue
        record = by_uid.get(directory.name, {})
        print(f"\n=== {record.get('collection', '?')} / {record.get('patient', directory.name[:16])}")
        try:
            result = analyse(directory)
        except Exception as error:  # noqa: BLE001 - a failure must be visible, not skipped
            print(f"    FAILED: {error}")
            everything.append({"series_uid": directory.name, "error": repr(error)})
            continue
        result["collection"] = record.get("collection")
        result["chosen_because"] = record.get("chosen_because")
        everything.append(result)

        print(f"    S = {result['table_speed_mm_s']} mm/s, {result['slices']} slices, "
              f"{result['z_span_mm']:.0f} mm scanned")
        print(f"    {'row':>5} {'period mm':>10} {'cycles':>7} {'p-p mm':>8} "
              f"{'resid mm':>9} {'sigma':>7} {'implied bpm':>12}")
        for level in result["levels"]:
            if not level.get("usable"):
                print(f"    {level['coronal_row']:>5}   no usable trace")
                continue
            rate = level["implied_heart_rate_bpm"]
            print(f"    {level['coronal_row']:>5} {level['period_mm']:>10.1f} "
                  f"{level['cycles_written']:>7.2f} {level['pulsation_peak_to_peak_mm']:>8.2f} "
                  f"{level['residual_sd_mm']:>9.2f} {level['sigma']:>7.2f} "
                  f"{rate:>12.0f}" if rate else "")

    destination = RESULTS / "border_traces.json"
    destination.write_text(json.dumps(everything, indent=2), encoding="utf-8")
    print(f"\nwritten: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
