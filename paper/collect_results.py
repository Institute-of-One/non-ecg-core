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

    out["header_patients"] = len({r["patient"] for r in cohort})
    per_collection = [sum(1 for r in cohort if r["collection"] == name)
                      for name in {r["collection"] for r in cohort}]
    # The cap, not the smallest contribution: an earlier version reported the minimum and
    # the arithmetic in the manuscript did not add up.
    out["header_series_cap"] = max(per_collection)
    out["header_collections_at_cap"] = sum(1 for n in per_collection
                                           if n == max(per_collection))
    out["header_smallest_collection"] = min(per_collection)

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


def failure_diagnosis_metrics() -> dict:
    """Step 7: how real traces differ from simulated ones, and by how much they do not.

    Added after the PMB inquiry quoted these figures without them being here -- the second
    time the rule caught a number reaching correspondence before it reached the manifest.
    The rule is working; my habit of writing prose before collecting is not.
    """
    data = _load("failure_diagnosis.json")
    real, simulated = data["real"], data["simulated"]
    out = {
        "diagnosis_traces_real": data["n_real"],
        "diagnosis_traces_simulated": data["n_simulated"],
        "baseline_share_real_percent": round(100 * real["baseline_share"]["median"]),
        "baseline_share_simulated_percent": round(100 * simulated["baseline_share"]["median"]),
        "band_enrichment_real": round(real["band_power_enrichment"]["median"], 1),
        "band_enrichment_simulated": round(simulated["band_power_enrichment"]["median"], 1),
    }
    # spread, which is the property that actually distinguishes the two populations
    for name, source in (("real", real), ("simulated", simulated)):
        span = source["band_power_fraction"]["p90"] - source["band_power_fraction"]["p10"]
        out[f"band_fraction_spread_{name}"] = round(span, 3)
    out["band_fraction_spread_ratio"] = round(
        out["band_fraction_spread_real"] / out["band_fraction_spread_simulated"], 1
    )
    # These were once two hand-typed literals asserting that four candidate explanations had
    # been put back into the simulator and none reproduced the failure. No such experiment is
    # in this repository: diagnose_failure.py measures properties, it does not test causes.
    # Everything here now comes from the file.
    out["diagnosis_properties"] = len(data["real"])
    out["amplitude_drift_real"] = round(data["real"]["amplitude_drift_ratio"]["median"], 2)
    out["amplitude_drift_simulated"] = round(
        data["simulated"]["amplitude_drift_ratio"]["median"], 2)
    out["large_steps_real_p90"] = round(data["real"]["large_steps_per_100"]["p90"], 1)
    out["large_steps_simulated_p90"] = round(
        data["simulated"]["large_steps_per_100"]["p90"], 1)
    return out


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


def cardiac_tag_metrics() -> dict:
    """Whether any analysed series records a cardiac timing field of its own.

    The premise that no reference heart rate exists is load-bearing, so it is quoted from a
    measurement rather than asserted. Produced by analysis/check_cardiac_tags.py.
    """
    data = _load("cardiac_tags.json")
    return {
        "cardiac_routes_checked": data["routes_checked"],
        "cardiac_standard_fields_checked": len(data["tags_checked"]),
        "cardiac_tag_series_checked": data["series_checked"],
        "cardiac_tag_series_with_field": data["series_with_any_cardiac_field"],
    }


def tcia_survey_metrics() -> dict:
    """How rare a public scan with a recorded rate is. From analysis/tcia_search/."""
    search = HERE.parent / "analysis" / "tcia_search"
    body_parts = json.loads((search / "tcia_bodyparts.json").read_text(encoding="utf-8"))
    studies = json.loads((search / "tcia_cardiac_studies.json").read_text(encoding="utf-8"))
    pairings = json.loads((search / "tcia_pairings.json").read_text(encoding="utf-8"))
    return {
        "tcia_collections_surveyed": len(body_parts),
        "tcia_collections_with_ct": sum(1 for v in body_parts.values() if "body_parts" in v),
        "tcia_cardiac_studies": len(studies["studies"]),
        "tcia_sessions_with_recorded_rate": len(pairings),
        "tcia_sessions_with_rate_and_helical": sum(1 for p in pairings if p["pairing"]),
    }


def reference_case_metrics() -> dict:
    """The one series whose true rate is known, under the protocol frozen before the run."""
    data = _load("reference_case.json")
    outcome = data["outcome"]
    recorded = data["reference_bpm"]
    period_s = 60.0 / recorded
    return {
        "reference_rate_recorded": recorded,
        "reference_rate_range_low": data["recorded_range_bpm"][0],
        "reference_rate_range_high": data["recorded_range_bpm"][1],
        "reference_band_low": round(data["agreement_band_bpm"][0], 2),
        "reference_band_high": round(data["agreement_band_bpm"][1], 2),
        "reference_rate_fitted": round(outcome["heart_rate_bpm"], 1),
        "reference_error_percent": round(
            100 * (outcome["heart_rate_bpm"] - recorded) / recorded, 1),
        "reference_z_span_mm": round(outcome["z_span_mm"]),
        "reference_table_speed": round(outcome["table_speed_mm_s"], 1),
        "reference_scan_seconds": round(outcome["z_span_mm"] / outcome["table_speed_mm_s"], 2),
        "reference_cycles_at_recorded_rate": round(
            outcome["z_span_mm"] / (outcome["table_speed_mm_s"] * period_s), 2),
        "reference_levels": outcome["levels"],
        "reference_loo_spread_bpm": round(outcome["leave_one_out_spread_bpm"], 1),
        "reference_median_sigma": round(outcome["median_sigma"], 3),
        "reference_rate_in_agreement": data["primary_rate_in_agreement"],
        "reference_self_consistent": data["secondary_self_consistent"],
    }


def learned_design_metrics() -> dict:
    """The estimator's architecture and training, from the module that defines them.

    Section 6 quotes a reported standard deviation of a few hundredths. Without the target's
    definition that figure has no units, so the design is read from the code rather than
    described from memory.
    """
    import sys                                                      # noqa: PLC0415
    sys.path.insert(0, str(HERE.parent / "analysis"))
    import learned_estimator as model                               # noqa: PLC0415

    above = model.CONDITIONS["trained_above_the_bound"]
    across = model.CONDITIONS["trained_across_the_boundary"]
    return {
        "learned_trace_length": model.TRACE_LENGTH,
        "learned_hidden_units": model.HIDDEN,
        "learned_epochs": model.EPOCHS,
        "learned_batch": model.BATCH,
        "learned_train_size": model.TRAIN_SIZE,
        "learned_test_per_point": model.TEST_PER_POINT,
        "learned_tolerance_percent": round(100 * model.TOLERANCE),
        "learned_above_low": above[0],
        "learned_above_high": above[1],
        "learned_across_low": across[0],
        "learned_across_high": across[1],
        # The target is the reciprocal of the cycles written, so the training range in
        # target units is what decides whether a test point is an extrapolation.
        "learned_above_target_low": round(1.0 / above[1], 3),
        "learned_above_target_high": round(1.0 / above[0], 3),
        "learned_across_target_high": round(1.0 / across[0], 2),
        "learned_target_at_two_cycles": 0.5,
        "learned_target_at_half_cycle": round(1.0 / min(model.TEST_CYCLES), 1),
    }


def border_metrics() -> dict:
    """Was the extraction on the mediastinum, or on the patient's outline?

    The pipeline never asked. Produced by analysis/check_border_position.py, which was
    written after a figure showed the tracked border lying on the skin for the one series
    whose heart rate is recorded.
    """
    data = _load("border_position.json")
    positions = {r["series_uid"]: r for r in data["series"]
                 if "median_fraction_of_width" in r}
    cohort = [s for s in _load("cohort_outcome.json")["series"] if "recovered" in s]
    reference = ("1.3.6.1.4.1.14519.5.2.1."
                 "264532322608206684963835753501167761257")

    def fraction(entry):
        return positions.get(entry["series_uid"], {}).get("median_fraction_of_width")

    admitted = [f for f in map(fraction, (s for s in cohort if s["recovered"])) if f]
    in_cohort = [(s, fraction(s)) for s in cohort]
    surface = [s for s, f in in_cohort if f is not None and f < 0.10]
    doubtful = [s for s, f in in_cohort if f is not None and 0.10 <= f < 0.35]
    sound = [f for _, f in in_cohort if f is not None and f >= 0.35]

    return {
        "border_series_checked": data["series_checked"],
        "border_surface_threshold_percent": round(100 * data["surface_fraction"]),
        "border_cohort_on_the_surface": len(surface),
        "border_cohort_doubtful": len(doubtful),
        "border_cohort_on_the_surface_all_rejected":
            all(not s["recovered"] for s in surface + doubtful),
        "border_sound_min_percent": round(100 * min(sound)),
        "border_sound_max_percent": round(100 * max(sound)),
        "border_admitted_min_percent": round(100 * min(admitted)),
        "border_admitted_max_percent": round(100 * max(admitted)),
        "border_reference_percent": round(100 * positions[reference]
                                          ["median_fraction_of_width"], 1),
        "border_reference_levels_on_surface": round(
            100 * positions[reference]["share_of_levels_at_the_surface"]),
    }


def extent_metrics() -> dict:
    """Cycles written depend on which length is used, and the paper uses two.

    Section 2 defines N over L, the craniocaudal extent of the structure that can carry the
    motion: 120 mm at the cardiac border, 300 mm along the descending aorta. The cohort code
    divides by the z span actually analysed, which for most series is close to the aortic
    extent but for a chin-to-pelvis acquisition is twice it. Keeping both here is what stops
    the manuscript quoting one and meaning the other.
    """
    border, aorta = 120.0, 300.0
    reference = _load("reference_case.json")
    outcome = reference["outcome"]
    wavelength = outcome["table_speed_mm_s"] * 60.0 / reference["reference_bpm"]

    cohort = [s for s in _load("cohort_outcome.json")["series"] if "recovered" in s]
    spans = sorted(s["z_span_mm"] for s in cohort)
    over_span = sum(1 for s in cohort if s["cycles_written"] >= 2.5)
    over_aorta = sum(1 for s in cohort if aorta / s["period_mm"] >= 2.5)

    return {
        "extent_border_mm": round(border),
        "extent_aorta_mm": round(aorta),
        "reference_wavelength_mm": round(wavelength, 1),
        "reference_cycles_border": round(border / wavelength, 2),
        "reference_cycles_aorta": round(aorta / wavelength, 2),
        "cohort_span_median_mm": round(spans[len(spans) // 2]),
        "cohort_span_min_mm": round(spans[0]),
        "cohort_span_max_mm": round(spans[-1]),
        "cohort_over_nmin_by_span": over_span,
        "cohort_over_nmin_by_aorta": over_aorta,
    }


def extraction_metrics() -> dict:
    """The constants the extraction and the joint fit are defined by, read from them."""
    import sys                                                      # noqa: PLC0415
    sys.path.insert(0, str(HERE.parent / "analysis"))
    import extract_border_trace as extraction                       # noqa: PLC0415
    import joint_period_fit as fit                                  # noqa: PLC0415

    return {
        "lung_threshold_hu": round(extraction.LUNG_THRESHOLD_HU),
        "min_mediastinum_mm": round(extraction.MIN_MEDIASTINUM_MM),
        "coronal_levels": len(fit.CORONAL_FRACTIONS),
        "coronal_fraction_low": min(fit.CORONAL_FRACTIONS),
        "coronal_fraction_high": max(fit.CORONAL_FRACTIONS),
        "band_slowest_bpm": round(fit.SLOWEST_BPM),
        "band_fastest_bpm": round(fit.FASTEST_BPM),
    }


def sweep_and_selection_metrics() -> dict:
    """The grid the sweep actually covered, and how the two sets of series were chosen."""
    sensitivity = _load("n_min_fundamental.json")["sensitivity"]
    headers = _load("cohort_headers.json")
    cohort = _load("cohort_outcome.json")["series"]
    pilots = _load("pilot_series.json")

    axes = {name: sorted({cell[name] for cell in sensitivity})
            for name in ("noise", "baseline", "samples_per_cycle", "variability")}
    header_uids = {r["series_uid"] for r in headers}
    return {
        "sweep_noise_levels": len(axes["noise"]),
        "sweep_noise_min": min(axes["noise"]),
        "sweep_noise_max": max(axes["noise"]),
        "sweep_baseline_levels": len(axes["baseline"]),
        "sweep_baseline_max": max(axes["baseline"]),
        "sweep_samples_levels": len(axes["samples_per_cycle"]),
        "sweep_samples_min": min(axes["samples_per_cycle"]),
        "sweep_samples_max": max(axes["samples_per_cycle"]),
        "sweep_variability_levels": len(axes["variability"]),
        "sweep_variability_max": max(axes["variability"]),
        "cohort_patients": len({r.get("patient") for r in cohort}),
        "cohort_from_header_set": len({r["series_uid"] for r in cohort} & header_uids),
        "pilot_series": len(pilots),
    }


def flatness_metrics() -> dict:
    """How much better the chosen period fits than a typical one in the band.

    1.00 would mean the best period fits no better than any other. The cohort's three
    acceptances sit at the same depth as its rejections, which is what identifies the
    acceptances as artefacts of a flat objective rather than as recoveries.
    """
    reference_uid = ("1.3.6.1.4.1.14519.5.2.1."
                     "264532322608206684963835753501167761257")
    flat = {r["series_uid"]: r for r in _load("flatness.json")["series"]}
    cohort = _load("cohort_outcome.json")["series"]

    def depth(entry):
        row = flat.get(entry["series_uid"], {})
        return row.get("median_over_min")

    def spread(entry):
        row = flat.get(entry["series_uid"], {})
        return row.get("level_preferred_spread_bpm")

    accepted = [s for s in cohort if s.get("recovered")]
    rejected = [s for s in cohort if not s.get("recovered")]
    accepted_depths = sorted(d for d in map(depth, accepted) if d)
    rejected_depths = sorted(d for d in map(depth, rejected) if d)
    accepted_spreads = sorted(s for s in map(spread, accepted) if s)

    return {
        "flatness_depth_accepted_min": round(accepted_depths[0], 3),
        "flatness_depth_accepted_max": round(accepted_depths[-1], 3),
        "flatness_depth_rejected_median": round(
            rejected_depths[len(rejected_depths) // 2], 3),
        "flatness_depth_rejected_min": round(rejected_depths[0], 3),
        "flatness_depth_rejected_max": round(rejected_depths[-1], 3),
        "flatness_level_spread_accepted_min": round(accepted_spreads[0]),
        "flatness_level_spread_accepted_max": round(accepted_spreads[-1]),
        "flatness_depth_reference": round(flat[reference_uid]["median_over_min"], 3),
        "flatness_level_spread_reference": round(
            flat[reference_uid]["level_preferred_spread_bpm"]),
    }


def reference_diagnosis_metrics() -> dict:
    """Was the true period missed by the search, or absent from the trace?"""
    data = _load("reference_case_diagnosis.json")
    return {
        "reference_true_period_in_band": data["true_period_in_band"],
        "reference_cost_true_over_fitted": round(data["cost_at_true_over_fitted"], 3),
        "reference_true_is_local_minimum": data["true_period_is_local_minimum"],
        "reference_grid_step_mm": round(data["grid_step_mm"], 2),
    }


def main() -> int:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    metrics = {}
    for section in (simulation_metrics, header_metrics, representative_protocol_metrics,
                    cohort_metrics, failure_diagnosis_metrics, learned_metrics,
                    cardiac_tag_metrics, tcia_survey_metrics, reference_case_metrics,
                    flatness_metrics, reference_diagnosis_metrics, extent_metrics,
                    border_metrics, learned_design_metrics,
                    sweep_and_selection_metrics, extraction_metrics):
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
