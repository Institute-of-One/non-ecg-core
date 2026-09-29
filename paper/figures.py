"""Every figure in the manuscript, drawn from the result files that produced the numbers.

No figure here reads an image or recomputes an analysis. Each one is a view of a file in
results/, or of the closed-form module in analysis/sampling_bound.py, so a figure cannot
drift from the manifest the prose quotes. A figure that needs a quantity absent from those
files is a figure the paper may not show.

    python paper/figures.py
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
REPO = HERE.parent
RESULTS = REPO / "results"
FIGURES = HERE / "figures"
sys.path.insert(0, str(REPO / "analysis"))

WIDE = (7.0, 4.0)
TALL = (7.0, 5.0)
DPI = 200

INK = "#1a1a1a"
ACCENT = "#b2182b"
SECOND = "#2166ac"
MUTED = "#9e9e9e"

plt.rcParams.update({
    "font.size": 9,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "savefig.bbox": "tight",
})


def load(name: str):
    path = RESULTS / name
    if not path.is_file():
        raise SystemExit(f"missing result file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save(figure, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    figure.savefig(path)
    plt.close(figure)
    return path


# ------------------------------------------------------------------ 1. the window

def figure_window() -> Path:
    """Cycles against samples per cycle, with the budget hyperbola and the real protocols."""
    from sampling_bound import (  # noqa: PLC0415
        HEART_EXTENT_MM, PROTOCOLS, cycles_written, samples_per_cycle,
    )

    n_min, samples_min = 2.5, 8.0
    cycle_s = 1.0                                   # 60 bpm, the reference rate of the table

    #: Full protocol names do not fit beside the points. Matched on a distinctive substring
    #: so that a renamed protocol loses its short label rather than acquiring a wrong one.
    short = {
        "row-pitch 6": "2003, pitch 6",
        "row-pitch 3": "2003, pitch 3 (aliased)",
        "thin recon": "routine chest, 0.6 mm recon",
        "pitch 1.0": "routine chest, 1.0 mm recon",
        "lung screening": "lung screening",
        "wide detector": "wide detector",
        "dual-source": "dual-source high pitch",
        "retrospective gating": "cardiac CT, gated",
    }
    #: Keyed on the same substrings, so a label and its offset cannot drift apart.
    #: The three modern chest protocols sit within a factor of two of one another, so their
    #: labels are placed well clear and joined by leader lines rather than nudged until they
    #: only just miss the N_min rule.
    offsets = {
        "row-pitch 6": (52, -14),
        "row-pitch 3": (52, 16),
        "pitch 1.0": (30, -22),
        "thin recon": (8, -48),
        "lung screening": (-30, -16),
        "wide detector": (10, 16),
        "dual-source": (8, -20),
        "retrospective gating": (-12, 12),
    }
    leadered = {"pitch 1.0", "thin recon", "lung screening",
                "row-pitch 3", "row-pitch 6"}

    figure, axis = plt.subplots(figsize=WIDE)
    x_lo, x_hi, y_lo, y_hi = 1.0, 3e3, 1e-2, 1e2

    # The recoverable region is the intersection of the two conditions, not their union.
    axis.add_patch(plt.Rectangle((samples_min, n_min), x_hi - samples_min, y_hi - n_min,
                                 color=SECOND, alpha=0.10, lw=0, zorder=0))
    axis.axhline(n_min, color=SECOND, lw=1.0)
    axis.axvline(samples_min, color=SECOND, lw=1.0)
    axis.text(1.15, n_min * 1.2, f"$N_{{\\min}}$ = {n_min}", color=SECOND, fontsize=8)
    axis.text(samples_min * 1.12, 1.15e-2, f"$n$ = {samples_min:.0f}",
              color=SECOND, fontsize=8, ha="left", va="bottom")
    recoverable_patch = plt.Rectangle((0, 0), 1, 1, color=SECOND, alpha=0.10, lw=0,
                                      label="recoverable: both conditions met")

    samples = np.logspace(0, 4, 400)
    for dz, style in ((0.6, "-"), (1.0, "--"), (2.0, ":")):
        axis.plot(samples, (HEART_EXTENT_MM / dz) / samples, style, color=MUTED, lw=1.1,
                  label=f"budget $N n = L/dz$, $dz$ = {dz} mm")

    for index, protocol in enumerate(PROTOCOLS):
        x = samples_per_cycle(protocol, cycle_s)
        y = cycles_written(protocol, cycle_s)
        recoverable = y >= n_min and x >= samples_min
        axis.plot(x, y, "o", ms=5, color=SECOND if recoverable else ACCENT,
                  mec="white", mew=0.6, zorder=5)
        key = next((k for k in short if k in protocol.name), None)
        label = short.get(key, protocol.name)
        dx, dy = offsets.get(key, (9, 6))
        axis.annotate(label, (x, y), textcoords="offset points", xytext=(dx, dy),
                      fontsize=6.8, color=INK, ha="left" if dx > 0 else "right",
                      va="bottom" if dy > 0 else "top",
                      arrowprops=dict(arrowstyle="-", lw=0.5, color=MUTED,
                                      shrinkA=0, shrinkB=3) if key in leadered else None)

    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlim(x_lo, x_hi)
    axis.set_ylim(y_lo, y_hi)
    axis.set_xlabel("samples per cardiac cycle, $n$")
    axis.set_ylabel("cardiac cycles written across the heart, $N$")
    axis.set_title("The recoverable region is the corner, and the budget is a straight line "
                   "through it", fontsize=9, loc="left")
    handles, labels = axis.get_legend_handles_labels()
    axis.legend([recoverable_patch] + handles, [recoverable_patch.get_label()] + labels,
                frameon=False, fontsize=7.5, loc="lower left",
                bbox_to_anchor=(0.0, 0.07))
    return save(figure, "fig1_window.png")


# ------------------------------------------------------------------ 2. N_min

def figure_n_min() -> Path:
    """The measured constant, and how far it moves across the sweep."""
    matched = load("n_min.json")
    fundamental = load("n_min_fundamental.json")

    figure, (left, right) = plt.subplots(1, 2, figsize=WIDE,
                                         gridspec_kw={"width_ratios": [1.5, 1]})

    for data, colour, label in ((matched, SECOND, "matched estimator"),
                                (fundamental, ACCENT, "fundamental estimator")):
        curve = data["central_curve"]
        left.plot([p["cycles"] for p in curve], [p["success_rate"] for p in curve],
                  "o-", ms=3.5, lw=1.4, color=colour, label=label)
        left.axvline(data["headline_n_min"], color=colour, lw=1.0, ls="--", alpha=0.7)

    target = fundamental["criterion"]["success_rate"]
    left.axhline(target, color=MUTED, lw=1.0)
    left.text(5.0, target - 0.07,
              f"{target:.0%} of {fundamental['criterion']['trials']} trials",
              fontsize=7.5, color=MUTED, ha="center")
    left.set_xlabel("cardiac cycles written, $N$")
    left.set_ylabel(f"fraction recovered within "
                    f"{fundamental['criterion']['tolerance']:.0%}")
    left.set_ylim(-0.03, 1.05)
    left.legend(frameon=False, fontsize=7.5, loc="lower right")
    left.set_title("$N_{\\min}$ is where the curve crosses", fontsize=9, loc="left")

    values = [c["n_min"] for c in fundamental["sensitivity"] if c["n_min"] is not None]
    edges = np.arange(min(values) - 0.25, max(values) + 0.75, 0.5)
    right.hist(values, bins=edges, color=ACCENT, alpha=0.85, rwidth=0.85)
    right.axvline(fundamental["headline_n_min"], color=INK, lw=1.2)
    right.set_xlabel("$N_{\\min}$ per parameter combination")
    right.set_ylabel(f"cells (of {len(fundamental['sensitivity'])})")
    right.set_title("and it barely moves", fontsize=9, loc="left")

    figure.tight_layout()
    return save(figure, "fig2_n_min.png")


# ------------------------------------------------------------------ 3. real protocols

def figure_protocols() -> Path:
    """The lowest rate each real series could record, at two available extents."""
    headers = load("cohort_headers.json")
    speeds = np.array([r["table_speed_mm_s"] for r in headers])
    n_min = 2.5
    ceiling = 100.0

    figure, axis = plt.subplots(figsize=WIDE)
    bins = np.logspace(np.log10(5), np.log10(400), 44)
    for extent, colour, label in ((300.0, SECOND, "descending aorta, $L$ = 300 mm"),
                                  (120.0, ACCENT, "cardiac border, $L$ = 120 mm")):
        thresholds = 60.0 * speeds * n_min / extent
        share = (thresholds <= ceiling).mean()
        axis.hist(thresholds, bins=bins, color=colour, alpha=0.55,
                  label=f"{label} — {share:.0%} below {ceiling:.0f} bpm")

    axis.axvline(ceiling, color=INK, lw=1.2)
    top = axis.get_ylim()[1]
    axis.set_ylim(0, top * 1.28)                     # room for the legend above the bars
    axis.text(ceiling * 1.06, top * 0.55, f"{ceiling:.0f} bpm", fontsize=8, rotation=90,
              va="center")
    axis.set_xscale("log")
    axis.set_xlabel("lowest heart rate the protocol could record (bpm)")
    axis.set_ylabel(f"series (of {len(headers)})")
    axis.set_title("On the installed base the acquisition condition is mostly satisfied",
                   fontsize=9, loc="left")
    axis.legend(frameon=False, fontsize=7.5, loc="upper left")
    return save(figure, "fig3_protocols.png")


# ------------------------------------------------------------------ 4. flatness

def figure_flatness() -> Path:
    """The admitted series are not deeper minima than the rejected ones."""
    reference_uid = ("1.3.6.1.4.1.14519.5.2.1."
                     "264532322608206684963835753501167761257")
    flat = {r["series_uid"]: r for r in load("flatness.json")["series"]}
    cohort = load("cohort_outcome.json")["series"]

    # A technical failure carries no `recovered` key and is neither admitted nor rejected;
    # counting it among the rejections would put a number in the axis label that no point
    # on the axis corresponds to.
    admitted = [s for s in cohort if s.get("recovered") is True]
    rejected = [s for s in cohort if s.get("recovered") is False]

    def depths(entries):
        return [flat[e["series_uid"]]["median_over_min"] for e in entries
                if e["series_uid"] in flat and "median_over_min" in flat[e["series_uid"]]]

    figure, (left, right) = plt.subplots(1, 2, figsize=WIDE,
                                         gridspec_kw={"width_ratios": [1, 1.25]})

    groups = [("rejected\n(n = %d)" % len(rejected), depths(rejected), MUTED),
              ("admitted\n(n = %d)" % len(admitted), depths(admitted), ACCENT),
              ("reference\ncase", [flat[reference_uid]["median_over_min"]], SECOND)]
    rng = np.random.default_rng(20260929)
    for position, (label, values, colour) in enumerate(groups):
        jitter = rng.uniform(-0.08, 0.08, len(values))
        left.plot(np.full(len(values), position) + jitter, values, "o", ms=6,
                  color=colour, mec="white", mew=0.7, alpha=0.9)
    left.axhline(1.0, color=INK, lw=1.0, ls="--")
    left.text(2.35, 1.003, "no better than\nan arbitrary period", fontsize=7, ha="right")
    left.set_xticks(range(len(groups)))
    left.set_xticklabels([g[0] for g in groups], fontsize=8)
    left.set_xlim(-0.5, len(groups) - 0.5)
    left.set_ylabel("depth of the minimum\n(median cost over the band / cost at the fit)")
    left.set_title("Depth does not separate them", fontsize=9, loc="left")

    shown = admitted + [{"series_uid": reference_uid,
                         "heart_rate_bpm": flat[reference_uid]["fitted_bpm"]}]
    for position, entry in enumerate(shown):
        row = flat[entry["series_uid"]]
        preferred = row["level_preferred_bpm"]
        colour = SECOND if entry["series_uid"] == reference_uid else ACCENT
        right.plot(np.full(len(preferred), position), preferred, "o", ms=5, color=MUTED,
                   mec="white", mew=0.6, alpha=0.95)
        right.plot(position, row["fitted_bpm"], "x", ms=10, mew=2.0, color=colour)
    right.set_xticks(range(len(shown)))
    right.set_xticklabels([f"admitted {i + 1}" for i in range(len(admitted))]
                          + ["reference"], fontsize=8, rotation=20)
    right.set_xlim(-0.5, len(shown) - 0.5)
    right.set_ylabel("heart rate (bpm)")
    right.set_title("Grey: what each coronal level prefers alone.  "
                    "Cross: the joint fit", fontsize=8, loc="left")

    figure.tight_layout()
    return save(figure, "fig4_flatness.png")


# ------------------------------------------------------------------ 5. what the fit reads

def figure_coronal() -> Path:
    """The border the whole paper is about, and the two waves that might be on it.

    This is the only figure that reads an image. It exists because the argument of section 2
    is visual — a coronal reformat in which the mediastinal silhouette is wavy because the
    table advanced while the heart beat — and the paper otherwise asserts that appearance
    without ever showing it.

    The level shown is the one whose independent fit comes closest to the joint fit, so the
    figure is the most favourable honest choice rather than the clearest-looking one.
    """
    import numpy as np                                            # noqa: PLC0415
    from extract_border_trace import left_border_trace, load_series   # noqa: PLC0415

    reference_uid = ("1.3.6.1.4.1.14519.5.2.1."
                     "264532322608206684963835753501167761257")
    positions = {r["series_uid"]: r for r in load("border_position.json")["series"]
                 if "median_fraction_of_width" in r}
    cohort = [s for s in load("cohort_outcome.json")["series"] if s.get("recovered")]
    # The admitted series whose border sits deepest, i.e. the clearest example of the
    # extraction doing what it was written to do. Chosen by the measurement, not by eye.
    sound_uid = max((s["series_uid"] for s in cohort),
                    key=lambda uid: positions[uid]["median_fraction_of_width"])
    row_fraction = 0.60

    figure, axes = plt.subplots(2, 1, figsize=(6.6, 6.4))
    for axis, uid, label in ((axes[0], sound_uid, "a chest CT from the cohort"),
                             (axes[1], reference_uid,
                              "the one series in the archive with a recorded heart rate")):
        volume = load_series(REPO / "data_cache" / uid)
        row = int(volume.array.shape[1] * row_fraction)
        coronal = volume.array[:, row, :]
        trace = left_border_trace(volume, row)
        finite = np.isfinite(trace)
        width = coronal.shape[1] * volume.spacing_xy_mm[1]
        share = positions[uid]["median_fraction_of_width"]
        colour = SECOND if share >= 0.35 else ACCENT

        # A reformat drawn at any aspect but its own is not a reformat. One millimetre
        # along z is one millimetre along x here, which is also what makes the second
        # panel's geometry — a scan twice as long as it is wide — visible at all.
        axis.imshow(coronal.T, cmap="gray", vmin=-1000, vmax=150, aspect="equal",
                    extent=[volume.z_mm[0], volume.z_mm[-1], width, 0],
                    interpolation="bilinear")
        axis.plot(volume.z_mm[finite], trace[finite], "-", color=colour, lw=1.4)

        # Below the line in both panels, so the label stays inside the image: in the lower
        # panel the border sits on the top edge and anything above it leaves the axes.
        mid = int(0.3 * len(volume.z_mm[finite]))
        axis.annotate("tracked border",
                      (volume.z_mm[finite][mid], trace[finite][mid]),
                      textcoords="offset points", xytext=(0, -30), ha="center", va="top",
                      fontsize=8, color=colour,
                      bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85),
                      arrowprops=dict(arrowstyle="->", color=colour, lw=1.0,
                                      shrinkA=2, shrinkB=1))
        axis.set_ylabel("x (mm)")
        axis.set_title(f"{label}: border at {share:.0%} of the image width",
                       fontsize=9, loc="left", color=INK if share >= 0.35 else ACCENT)
    axes[1].set_xlabel("z (mm) — and, at a constant table speed, time")
    figure.tight_layout()
    return save(figure, "fig5_coronal.png")


# ------------------------------------------------------------------ 6. the reference case

def figure_reference_case() -> Path:
    """The cost curve of the one series whose rate is recorded."""
    diagnosis = load("reference_case_diagnosis.json")
    case = load("reference_case.json")
    curve = diagnosis["cost_curve"]
    bpm = np.array(curve["bpm"])
    cost = np.array(curve["cost_over_fitted"])
    order = np.argsort(bpm)

    figure, axis = plt.subplots(figsize=WIDE)
    axis.axvspan(*case["recorded_range_bpm"], color=SECOND, alpha=0.18,
                 label="rate the scanner recorded, %.0f–%.0f bpm"
                       % tuple(case["recorded_range_bpm"]))
    axis.axvspan(*case["agreement_band_bpm"], color=SECOND, alpha=0.08,
                 label="agreement interval fixed before download")
    axis.plot(bpm[order], cost[order], "-", color=INK, lw=1.3)

    fitted = case["outcome"]["heart_rate_bpm"]
    axis.plot(fitted, 1.0, "o", ms=7, color=ACCENT, mec="white", mew=0.8, zorder=5)
    axis.annotate(f"the fit: {fitted:.1f} bpm", (fitted, 1.0), textcoords="offset points",
                  xytext=(-10, 10), fontsize=8, color=ACCENT, ha="right")

    recorded = case["reference_bpm"]
    at_recorded = float(np.interp(recorded, bpm[order], cost[order]))
    axis.plot(recorded, at_recorded, "o", ms=7, color=SECOND, mec="white", mew=0.8, zorder=5)
    axis.annotate(f"the recorded rate: {recorded:.0f} bpm\nnot a local minimum",
                  (recorded, at_recorded), textcoords="offset points", xytext=(10, 6),
                  fontsize=8, color=SECOND)

    axis.set_xlabel("heart rate (bpm)")
    axis.set_ylabel("cost, relative to the minimum")
    axis.set_title("The whole physiological band is within %.0f per cent of the best fit"
                   % ((cost.max() - 1.0) * 100), fontsize=9, loc="left")
    axis.legend(frameon=False, fontsize=7.5, loc="upper center")
    return save(figure, "fig6_reference_case.png")


# ------------------------------------------------------------------ 6. the estimator

def figure_estimator() -> Path:
    """Accuracy and declared uncertainty, for the two training conditions."""
    data = load("learned_estimator.json")
    n_min = 2.5
    conditions = (("trained_above_the_bound", ACCENT, "trained inside the bound"),
                  ("trained_across_the_boundary", SECOND, "trained across the boundary"))

    figure, (top, bottom) = plt.subplots(2, 1, figsize=TALL, sharex=True)
    for key, colour, label in conditions:
        rows = data["conditions"][key]
        cycles = [r["cycles"] for r in rows]
        top.plot(cycles, [r["accuracy"] for r in rows], "o-", ms=4, lw=1.4,
                 color=colour, label=label)
        bottom.plot(cycles, [r["median_reported_sd"] for r in rows], "o-", ms=4, lw=1.4,
                    color=colour)
        bottom.plot(cycles, [r["median_abs_error"] for r in rows], "s--", ms=3.5, lw=1.1,
                    color=colour, alpha=0.65)

    for axis in (top, bottom):
        axis.axvline(n_min, color=INK, lw=1.0, ls="--")
    top.text(n_min * 1.03, 0.5, "$N_{\\min}$", fontsize=8)
    top.set_ylabel(f"fraction within {data['tolerance']:.0%}")
    top.set_ylim(-0.05, 1.08)
    top.legend(frameon=False, fontsize=7.5, loc="lower right")
    top.set_title("Below the bound the model trained inside it is never right, "
                  "and declares the smallest uncertainty of either", fontsize=9, loc="left")

    bottom.set_yscale("log")
    bottom.set_xlabel("cardiac cycles written, $N$")
    bottom.set_ylabel("circles: declared s.d.\nsquares: error actually made")
    figure.tight_layout()
    return save(figure, "fig7_estimator.png")


def main() -> int:
    builders = (figure_window, figure_n_min, figure_protocols, figure_flatness,
                figure_coronal, figure_reference_case, figure_estimator)
    written = [builder() for builder in builders]
    if len(written) != len(builders):
        raise SystemExit("a figure was skipped; a missing figure must not pass silently")
    for path in written:
        print(f"  {path.relative_to(REPO)}  {path.stat().st_size // 1024} kB")
    print(f"\n{len(written)} figures written to {FIGURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
