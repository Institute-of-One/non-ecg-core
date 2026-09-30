"""Post-hoc anatomical audit: draw every usable coronal level of every admitted series.

Why this exists. Section 5.4 reports where the tracked border sits as a fraction of the image
width, which detects one failure — a border out at the patient's surface — and no other. Until
this script was written, exactly one of the admitted series had been looked at as an image
(figure 4 of the manuscript); the other two were assumed on the strength of the position number
alone. That is not the same thing, and the manuscript said so rather than fixing it.

What it does. For each series the frozen cohort admitted, it draws the coronal reformat at every
row that yielded a usable trace, with the tracked border on it, at the reformat's own aspect. One
page per series. Alongside each panel it records the quantities that would show a wrong structure
without anyone looking: where the border sits across the image, how far it wanders, how often the
tracker found no candidate, and whether the trace is constant to numerical precision at any point
— the signature that caught the reference case of section 5.4.

What it does NOT do. It does not re-run the fit, does not change the frozen cohort outcome, and
does not score the period against anything. It answers one question: was the thing measured the
thing intended?

    python analysis/audit_admitted_levels.py

Writes results/admitted_level_audit.json and paper/figures/audit_admitted_<n>.png. The images are
for a person to look at; the JSON is what the manuscript may quote.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
import numpy as np                                                 # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from extract_border_trace import left_border_trace, load_series     # noqa: E402
from joint_period_fit import CORONAL_FRACTIONS, MIN_SLICES_PER_LEVEL  # noqa: E402

REPO = HERE.parent
CACHE = REPO / "data_cache"
RESULTS = REPO / "results"
FIGURES = REPO / "paper" / "figures"

INK, GOOD, BAD = "#1b1b1b", "#0b6e4f", "#b3261e"

#: A border this close to the image edge is not the mediastinum (section 5.4's threshold).
SURFACE_FRACTION = 0.10
#: Below this fraction of the width the border is closer to the edge than to the middle.
DOUBTFUL_FRACTION = 0.35

#: A point on the intended border has aerated lung on one side of it and soft tissue on the
#: other. Looking at the audit images showed the tracker returning a "border" beyond the lung
#: base, where both sides are soft tissue at about 0 HU and no such interface exists. These two
#: thresholds are deliberately loose, so that only unambiguous cases are counted as failures.
LUNG_HU = -400.0
SOFT_TISSUE_HU = -100.0
#: How far either side of the border the means are taken.
PROBE_MM = 8.0


def interface_check(volume, row: int, trace, finite) -> dict:
    """Does each returned border actually separate aerated lung from soft tissue?

    The position check of section 5.4 asks only where the border sits across the image. It
    passes a border that sits near the middle of the image but below the lung base, where the
    two sides are both soft tissue and there is no lung-mediastinum interface at all.
    """
    spacing = volume.spacing_xy_mm[1]
    probe = max(2, int(PROBE_MM / spacing))
    verdicts = []
    for index in np.flatnonzero(finite):
        column = int(trace[index] / spacing)
        profile = volume.array[index, row, :]
        left = profile[max(0, column - probe):column]
        right = profile[column:column + probe]
        if left.size == 0 or right.size == 0:
            verdicts.append(False)
            continue
        verdicts.append(bool(left.mean() <= LUNG_HU and right.mean() >= SOFT_TISSUE_HU))
    verdicts = np.array(verdicts, dtype=bool)
    z = volume.z_mm[finite]
    return {
        "points": int(verdicts.size),
        "points_at_a_lung_interface": int(verdicts.sum()),
        "share_at_a_lung_interface": round(float(verdicts.mean()), 3),
        "z_span_all_mm": round(float(z[-1] - z[0]), 1),
        "z_span_valid_mm": (round(float(z[verdicts][-1] - z[verdicts][0]), 1)
                            if verdicts.any() else 0.0),
    }


def measure_level(volume, row: int, width_mm: float) -> dict:
    trace = left_border_trace(volume, row)
    finite = np.isfinite(trace)
    if finite.sum() < MIN_SLICES_PER_LEVEL:
        return {"row": row, "usable": False, "slices_with_border": int(finite.sum())}
    values = trace[finite]
    # A run of identical values means the tracker locked onto something that does not move.
    # On the reference case of section 5.4 one level was constant across the whole scan.
    diffs = np.diff(values)
    longest_flat = 0
    current = 0
    for d in diffs:
        current = current + 1 if d == 0.0 else 0
        longest_flat = max(longest_flat, current)
    return {
        "row": row,
        "usable": True,
        "slices_with_border": int(finite.sum()),
        "slices_total": int(trace.size),
        "gap_share": round(float(1.0 - finite.mean()), 3),
        "median_fraction_of_width": round(float(np.median(values) / width_mm), 3),
        "min_fraction_of_width": round(float(values.min() / width_mm), 3),
        "max_fraction_of_width": round(float(values.max() / width_mm), 3),
        "excursion_mm": round(float(values.max() - values.min()), 1),
        "sd_mm": round(float(values.std()), 2),
        "longest_constant_run": int(longest_flat + 1) if longest_flat else 0,
        **interface_check(volume, row, trace, finite),
    }


def draw_series(uid: str, index: int, levels: list[dict]) -> Path:
    volume = load_series(CACHE / uid)
    width_mm = volume.array.shape[2] * volume.spacing_xy_mm[1]
    usable = [level for level in levels if level["usable"]]
    figure, axes = plt.subplots(len(usable), 1, figsize=(13.0, 3.1 * len(usable)),
                                squeeze=False)
    for axis, level in zip(axes[:, 0], usable):
        row = level["row"]
        coronal = volume.array[:, row, :]
        trace = left_border_trace(volume, row)
        finite = np.isfinite(trace)
        share = level["median_fraction_of_width"]
        colour = GOOD if share >= DOUBTFUL_FRACTION else BAD
        axis.imshow(coronal.T, cmap="gray", vmin=-1000, vmax=150, aspect="equal",
                    extent=[volume.z_mm[0], volume.z_mm[-1], width_mm, 0],
                    interpolation="bilinear")
        axis.plot(volume.z_mm[finite], trace[finite], "-", color=colour, lw=1.0)
        # Crop x to a band around the border so the anatomy either side of it is legible.
        # The aspect stays equal, so the picture is still a reformat and not a stretch.
        centre = float(np.median(trace[finite]))
        axis.set_ylim(min(width_mm, centre + 110.0), max(0.0, centre - 110.0))
        axis.set_title(
            f"row {row} ({row / volume.array.shape[1]:.2f} of height): "
            f"{share:.0%} of width, excursion {level['excursion_mm']:.0f} mm, "
            f"{level['gap_share']:.0%} of slices empty"
            + (f", CONSTANT over {level['longest_constant_run']} slices"
               if level["longest_constant_run"] > 20 else ""),
            fontsize=9, loc="left", color=INK if share >= DOUBTFUL_FRACTION else BAD)
        axis.set_ylabel("x (mm)", fontsize=8)
        axis.tick_params(labelsize=7)
    axes[-1, 0].set_xlabel("z (mm)", fontsize=8)
    figure.suptitle(f"admitted series {index}: {uid[-16:]}", fontsize=10, x=0.01, ha="left")
    figure.tight_layout(rect=(0, 0, 1, 0.985))
    path = FIGURES / f"audit_admitted_{index}.png"
    figure.savefig(path, dpi=140)
    plt.close(figure)
    return path


def main() -> int:
    cohort = json.loads((RESULTS / "cohort_outcome.json").read_text(encoding="utf-8"))["series"]
    admitted = [s["series_uid"] for s in cohort if s.get("recovered")]
    if not admitted:
        raise SystemExit("no admitted series in the frozen cohort outcome")
    FIGURES.mkdir(parents=True, exist_ok=True)

    record = {
        "what_this_is": ("A post-hoc anatomical audit of the series the frozen criterion "
                         "admitted. It does not alter the cohort outcome of section 5.1."),
        "surface_fraction": SURFACE_FRACTION,
        "doubtful_fraction": DOUBTFUL_FRACTION,
        "min_slices_per_level": MIN_SLICES_PER_LEVEL,
        "series": [],
    }
    for index, uid in enumerate(admitted, 1):
        directory = CACHE / uid
        if not directory.is_dir():
            raise SystemExit(f"series not cached: {uid}. Fetch it before auditing.")
        volume = load_series(directory)
        width_mm = volume.array.shape[2] * volume.spacing_xy_mm[1]
        height = volume.array.shape[1]
        levels = [measure_level(volume, int(height * f), width_mm) for f in CORONAL_FRACTIONS]
        usable = [level for level in levels if level["usable"]]
        image = draw_series(uid, index, levels)
        record["series"].append({
            "index": index,
            "series_uid": uid,
            "image_width_mm": round(width_mm),
            "levels_attempted": len(CORONAL_FRACTIONS),
            "levels_usable": len(usable),
            "image": str(image.relative_to(REPO)).replace("\\", "/"),
            "levels": levels,
        })
        print(f"series {index}: {len(usable)} of {len(CORONAL_FRACTIONS)} rows usable -> {image}")
        for level in usable:
            flag = "" if level["median_fraction_of_width"] >= DOUBTFUL_FRACTION else "  EDGE"
            if level["share_at_a_lung_interface"] < 1.0:
                flag += (f"  <-- {level['points'] - level['points_at_a_lung_interface']} "
                         f"point(s) not at a lung interface")
            print(f"    row {level['row']:4d}  {level['median_fraction_of_width']:.3f} of width"
                  f"  excursion {level['excursion_mm']:5.1f} mm  gaps {level['gap_share']:.2f}"
                  f"  flat run {level['longest_constant_run']:4d}"
                  f"  at a lung interface {level['share_at_a_lung_interface']:.0%}"
                  f"  span {level['z_span_valid_mm']:5.0f} of {level['z_span_all_mm']:5.0f} mm"
                  f"{flag}")

    everything = [level for s in record["series"] for level in s["levels"] if level["usable"]]
    points = sum(level["points"] for level in everything)
    valid = sum(level["points_at_a_lung_interface"] for level in everything)
    record["summary"] = {
        "levels_audited": len(everything),
        "border_points": points,
        "border_points_at_a_lung_interface": valid,
        "share_at_a_lung_interface": round(valid / points, 3),
        "levels_wholly_at_a_lung_interface":
            sum(1 for level in everything if level["share_at_a_lung_interface"] == 1.0),
        "levels_below_the_surface_threshold":
            sum(1 for level in everything
                if level["median_fraction_of_width"] < SURFACE_FRACTION),
        "worst_level_share": min(level["share_at_a_lung_interface"] for level in everything),
        "max_gap_share": max(level["gap_share"] for level in everything),
    }
    print(f"\n{record['summary']}")

    (RESULTS / "admitted_level_audit.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten: {RESULTS / 'admitted_level_audit.json'}")
    print("Now LOOK at the images. The numbers cannot tell you what structure it is.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
