"""Measure how many cardiac cycles a scan must write before its period can be recovered.

The design is frozen in docs/step3_protocol.md and was committed before this file existed.
Nothing here chooses a criterion; it applies the one already fixed.

The estimator is given the true waveform and fits only its period, amplitude, phase and
the anatomical baseline. That is more than any real method knows, on purpose: the number
being measured is a bound, and an estimator that has to discover the waveform cannot need
fewer cycles than one that is handed it.

    python analysis/measure_n_min.py            # run the sweep, write results/n_min.json
    python analysis/measure_n_min.py --quick    # the central condition only
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"

# ------------------------------------------------------------------ frozen criterion

TOLERANCE = 0.05  #: a trial succeeds when the period is recovered to within 5%
SUCCESS_RATE = 0.90  #: N_min is the smallest N reaching this success rate
TRIALS = 200
ROOT_SEED = 20260906

CYCLE_GRID = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0)
NOISE_LEVELS = (0.05, 0.10, 0.20, 0.40)
BASELINE_LEVELS = (0.0, 0.5, 1.0, 2.0)
SAMPLES_PER_CYCLE = (8, 16, 32)
VARIABILITY = (0.0, 0.05, 0.10)

#: The one cell whose answer is the headline. Every other cell is sensitivity.
CENTRAL = {"noise": 0.10, "baseline": 1.0, "samples_per_cycle": 16, "variability": 0.05}


# ---------------------------------------------------------------------- signal model


def waveform(phase: np.ndarray) -> np.ndarray:
    """One cardiac cycle, asymmetric: contraction faster than filling.

    A pure sinusoid is easier to find than the real border trace and would understate the
    answer, so two harmonics with a fixed relative phase are used and the result is
    normalised to unit peak-to-peak.
    """
    wave = np.cos(2 * np.pi * phase) + 0.35 * np.cos(4 * np.pi * phase + np.pi / 4)
    return wave / (wave.max() - wave.min()) if wave.size else wave


_REFERENCE = waveform(np.linspace(0, 1, 4096, endpoint=False))
_SCALE = _REFERENCE.max() - _REFERENCE.min()


def _unit_waveform(phase: np.ndarray) -> np.ndarray:
    wave = np.cos(2 * np.pi * phase) + 0.35 * np.cos(4 * np.pi * phase + np.pi / 4)
    return wave / _SCALE


@dataclass(frozen=True)
class Trace:
    z: np.ndarray
    b: np.ndarray
    true_period: float


def simulate(cycles: float, samples_per_cycle: int, noise: float, baseline: float,
             variability: float, rng: np.random.Generator) -> Trace:
    """One cardiac border trace along z, as a helical scan would write it."""
    period = 1.0  # the spatial period, in arbitrary length units; only ratios matter
    total_length = cycles * period
    count = max(int(round(cycles * samples_per_cycle)), 4)
    z = np.linspace(0.0, total_length, count, endpoint=False)

    # Heart-rate variability makes the phase advance unevenly, which is what an irregular
    # rhythm does to the trace. Cumulative, so successive cycles drift rather than jitter
    # about a fixed grid.
    if variability > 0:
        steps = rng.normal(1.0, variability, size=count)
        phase = np.cumsum(steps) * (z[1] - z[0]) / period if count > 1 else np.zeros(count)
    else:
        phase = z / period
    phase = phase + rng.uniform(0, 1)

    motion = _unit_waveform(phase)

    # The anatomical envelope: the border moves along z because the heart is not a
    # cylinder, not only because it beats. This is the confound, not the noise.
    if baseline > 0 and total_length > 0:
        u = z / total_length
        coefficients = rng.normal(0, 1, size=3)
        envelope = coefficients[0] + coefficients[1] * u + coefficients[2] * u**2
        span = envelope.max() - envelope.min()
        envelope = envelope / span * baseline if span > 0 else envelope * 0
    else:
        envelope = np.zeros_like(z)

    b = motion + envelope + rng.normal(0, noise, size=count)
    return Trace(z=z, b=b, true_period=period)


# ------------------------------------------------------------------------- estimator


#: Amendment v1.1. The matched estimator's model spans exactly the terms the waveform is
#: built from, so it measures a floor rather than what a method would really need. These
#: two do not know the shape: one assumes only periodicity, the other only repetition.
ESTIMATORS = ("matched", "fundamental", "autocorrelation")


def _residual_for_period(trace: Trace, period: float, harmonics: int = 2) -> float:
    """Best achievable residual at this period, with everything else solved exactly.

    Amplitude, phase and the quadratic baseline all enter linearly once the period is
    fixed, so they are solved by least squares rather than searched. Only the period is
    searched, which is the quantity the bound is about.
    """
    u = trace.z / period
    total = trace.z[-1] - trace.z[0]
    v = trace.z / total if total > 0 else trace.z
    columns = [np.cos(2 * np.pi * u), np.sin(2 * np.pi * u)]
    if harmonics >= 2:
        columns += [np.cos(4 * np.pi * u), np.sin(4 * np.pi * u)]
    columns += [np.ones_like(v), v, v**2]
    design = np.column_stack(columns)
    solution, *_ = np.linalg.lstsq(design, trace.b, rcond=None)
    return float(np.sum((trace.b - design @ solution) ** 2))


def _detrended(trace: Trace) -> np.ndarray:
    """Remove the quadratic anatomical envelope, leaving whatever repeats.

    The baseline is part of the problem, not part of what an estimator is allowed to be
    ignorant of, so every estimator here removes it the same way.
    """
    total = trace.z[-1] - trace.z[0]
    v = trace.z / total if total > 0 else trace.z
    design = np.column_stack([np.ones_like(v), v, v**2])
    solution, *_ = np.linalg.lstsq(design, trace.b, rcond=None)
    return trace.b - design @ solution


def _period_by_autocorrelation(trace: Trace, true_period: float) -> float:
    """The first prominent peak of the autocorrelation, knowing nothing about the shape.

    An autocorrelation cannot see a lag longer than the trace, so below two written cycles
    this method has nowhere to find the period. That is a real limitation of the method
    and is left in rather than patched around.
    """
    signal = _detrended(trace)
    if signal.size < 8 or not np.any(signal):
        return float("nan")
    signal = signal - signal.mean()
    correlation = np.correlate(signal, signal, mode="full")[signal.size - 1:]
    if correlation[0] <= 0:
        return float("nan")
    correlation = correlation / correlation[0]
    step = trace.z[1] - trace.z[0]
    lowest = max(int(np.ceil(0.3 * true_period / step)), 2)
    highest = min(int(np.floor(3.0 * true_period / step)), correlation.size - 2)
    if highest <= lowest:
        return float("nan")
    window = correlation[lowest:highest + 1]
    peaks = [
        index for index in range(1, window.size - 1)
        if window[index] > window[index - 1] and window[index] >= window[index + 1]
    ]
    if not peaks:
        return float("nan")
    best = max(peaks, key=lambda index: window[index]) + lowest
    left, middle, right = correlation[best - 1], correlation[best], correlation[best + 1]
    denominator = left - 2 * middle + right
    offset = 0.5 * (left - right) / denominator if denominator != 0 else 0.0
    return float((best + offset) * step)


def estimate_period(trace: Trace, true_period: float, estimator: str = "matched") -> float:
    """Search a wide grid of periods, then refine parabolically about the best.

    The grid spans 0.3 to 3.0 times the truth so that a wrong period is an answer the
    estimator is able to give. A search bracketing only the right answer would measure
    nothing.
    """
    if estimator == "autocorrelation":
        return _period_by_autocorrelation(trace, true_period)
    harmonics = 2 if estimator == "matched" else 1
    grid = np.geomspace(0.3 * true_period, 3.0 * true_period, 400)
    residuals = np.array([_residual_for_period(trace, period, harmonics) for period in grid])
    best = int(np.argmin(residuals))
    if 0 < best < len(grid) - 1:
        left, middle, right = residuals[best - 1], residuals[best], residuals[best + 1]
        denominator = left - 2 * middle + right
        if denominator != 0:
            offset = 0.5 * (left - right) / denominator
            log_grid = np.log(grid)
            step = log_grid[best + 1] - log_grid[best]
            return float(np.exp(log_grid[best] + offset * step))
    return float(grid[best])


# ------------------------------------------------------------------------ the sweep


def success_rate(cycles: float, samples_per_cycle: int, noise: float, baseline: float,
                 variability: float, trials: int = TRIALS, seed: int = ROOT_SEED,
                 estimator: str = "matched") -> float:
    rng = np.random.default_rng(
        [seed, int(cycles * 10), samples_per_cycle, int(noise * 100),
         int(baseline * 10), int(variability * 100)]
    )
    hits = 0
    for _ in range(trials):
        trace = simulate(cycles, samples_per_cycle, noise, baseline, variability, rng)
        estimated = estimate_period(trace, trace.true_period, estimator)
        if np.isfinite(estimated) and abs(estimated - trace.true_period) / trace.true_period <= TOLERANCE:
            hits += 1
    return hits / trials


def n_min_for(samples_per_cycle: int, noise: float, baseline: float, variability: float,
              trials: int = TRIALS, estimator: str = "matched") -> tuple[float | None, list]:
    """The smallest N on the grid reaching the fixed success rate, and the curve."""
    curve = []
    found = None
    for cycles in CYCLE_GRID:
        rate = success_rate(cycles, samples_per_cycle, noise, baseline, variability,
                            trials, estimator=estimator)
        curve.append({"cycles": cycles, "success_rate": rate})
        if found is None and rate >= SUCCESS_RATE:
            found = cycles
    return found, curve


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="central condition only")
    parser.add_argument("--trials", type=int, default=TRIALS)
    parser.add_argument("--estimator", choices=ESTIMATORS, default="matched",
                        help="matched is the floor; fundamental is the headline")
    arguments = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    print(f"criterion: period within {TOLERANCE:.0%}, success rate {SUCCESS_RATE:.0%}, "
          f"{arguments.trials} trials per cell\n")

    headline, curve = n_min_for(
        CENTRAL["samples_per_cycle"], CENTRAL["noise"], CENTRAL["baseline"],
        CENTRAL["variability"], arguments.trials, estimator=arguments.estimator,
    )
    print("=== central condition "
          f"(noise {CENTRAL['noise']}, baseline {CENTRAL['baseline']}, "
          f"{CENTRAL['samples_per_cycle']} samples/cycle, "
          f"variability {CENTRAL['variability']:.0%})")
    for point in curve:
        marker = " <- N_min" if point["cycles"] == headline else ""
        print(f"    N = {point['cycles']:>4.1f}   success {point['success_rate']:6.1%}{marker}")
    print(f"\n    N_min = {headline}")

    output = {
        "estimator": arguments.estimator,
        "criterion": {"tolerance": TOLERANCE, "success_rate": SUCCESS_RATE,
                      "trials": arguments.trials, "root_seed": ROOT_SEED},
        "central_condition": CENTRAL,
        "headline_n_min": headline,
        "central_curve": curve,
        "sensitivity": [],
    }

    if not arguments.quick:
        print("\n=== sensitivity")
        print(f"    {'noise':>6} {'baseline':>9} {'n/cycle':>8} {'variability':>12} {'N_min':>7}")
        for noise in NOISE_LEVELS:
            for baseline in BASELINE_LEVELS:
                for samples in SAMPLES_PER_CYCLE:
                    for variability in VARIABILITY:
                        value, _ = n_min_for(samples, noise, baseline, variability,
                                             arguments.trials,
                                             estimator=arguments.estimator)
                        output["sensitivity"].append(
                            {"noise": noise, "baseline": baseline,
                             "samples_per_cycle": samples, "variability": variability,
                             "n_min": value}
                        )
                        shown = "none" if value is None else f"{value:.1f}"
                        print(f"    {noise:>6.2f} {baseline:>9.1f} {samples:>8d} "
                              f"{variability:>11.0%} {shown:>7}")

    destination = RESULTS / f"n_min_{arguments.estimator}.json"
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nwritten: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
