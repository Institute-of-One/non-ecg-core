"""Train an estimator that reports its own uncertainty, and ask whether it abstains.

Frozen design in docs/step6_protocol_learned_estimator.md, committed before this file
existed. Nothing here chooses a criterion.

The model predicts a period and a standard deviation, trained with a Gaussian negative
log-likelihood. Predicting uncertainty is what makes abstention possible; a model given
that ability and still refusing to use it has no excuse left.

    python analysis/learned_estimator.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from measure_n_min import CENTRAL, simulate  # noqa: E402

RESULTS = HERE.parent / "results"

# One definition of each, in a module the manifest builder can import without torch.
from learned_design import (  # noqa: E402
    BATCH,
    CONDITIONS,
    EPOCHS,
    HIDDEN,
    ROOT_SEED,
    TEST_CYCLES,
    TEST_PER_POINT,
    TOLERANCE,
    TRACE_LENGTH,
    TRAIN_SIZE,
)


def _detrend(z: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Remove the quartic baseline, exactly as every other estimator here does."""
    span = z[-1] - z[0]
    v = (z - z[0]) / span if span > 0 else z
    design = np.column_stack([np.ones_like(v), v, v**2, v**3, v**4])
    solution, *_ = np.linalg.lstsq(design, values, rcond=None)
    return values - design @ solution


def make_example(cycles: float, rng: np.random.Generator):
    """One trace, resampled to a fixed length, with its true period in trace units.

    The period is expressed as a fraction of the trace length rather than in absolute
    units, because the model sees a resampled trace and cannot know the scale. That is the
    same information the hand-built estimator had: the period relative to what was scanned.
    """
    trace = simulate(
        cycles,
        CENTRAL["samples_per_cycle"],
        CENTRAL["noise"],
        CENTRAL["baseline"],
        CENTRAL["variability"],
        rng,
    )
    signal = _detrend(trace.z, trace.b)
    spread = float(np.std(signal))
    if spread > 0:
        signal = signal / spread
    resampled = np.interp(
        np.linspace(0.0, 1.0, TRACE_LENGTH),
        np.linspace(0.0, 1.0, signal.size),
        signal,
    )
    # cycles written across the trace is exactly trace_length / period, so the target is
    # its reciprocal: the period as a fraction of the trace.
    return resampled.astype(np.float32), np.float32(1.0 / cycles)


def build_set(size: int, low: float, high: float, seed: int):
    rng = np.random.default_rng(seed)
    x = np.empty((size, TRACE_LENGTH), dtype=np.float32)
    y = np.empty((size, 1), dtype=np.float32)
    for index in range(size):
        cycles = float(rng.uniform(low, high))
        x[index], y[index, 0] = make_example(cycles, rng)
    return torch.from_numpy(x), torch.from_numpy(y)


class PeriodWithUncertainty(nn.Module):
    """Predicts the period and the log-variance of its own error."""

    def __init__(self) -> None:
        super().__init__()
        self.body = nn.Sequential(
            nn.Linear(TRACE_LENGTH, HIDDEN), nn.ReLU(),
            nn.Linear(HIDDEN, HIDDEN), nn.ReLU(),
            nn.Linear(HIDDEN, HIDDEN), nn.ReLU(),
        )
        self.mean = nn.Linear(HIDDEN, 1)
        self.log_variance = nn.Linear(HIDDEN, 1)

    def forward(self, x):
        h = self.body(x)
        # Clamped so the loss cannot be driven to negative infinity by an overconfident or
        # infinitely humble variance; the range spans four orders of magnitude in sigma.
        return self.mean(h), self.log_variance(h).clamp(-12.0, 4.0)


def gaussian_nll(prediction, log_variance, target):
    return (0.5 * (log_variance + (target - prediction) ** 2 / log_variance.exp())).mean()


def train(low: float, high: float, seed: int) -> PeriodWithUncertainty:
    torch.manual_seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    x, y = build_set(TRAIN_SIZE, low, high, seed)
    x, y = x.to(device), y.to(device)
    model = PeriodWithUncertainty().to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=1e-3)
    for epoch in range(EPOCHS):
        order = torch.randperm(x.shape[0], device=device)
        total = 0.0
        for start in range(0, x.shape[0], BATCH):
            batch = order[start:start + BATCH]
            mean, log_variance = model(x[batch])
            loss = gaussian_nll(mean, log_variance, y[batch])
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
            total += float(loss) * batch.numel()
        if (epoch + 1) % 10 == 0:
            print(f"      epoch {epoch + 1:>3}  NLL {total / x.shape[0]:+.4f}")
    return model


def evaluate(model: PeriodWithUncertainty, seed: int) -> list[dict]:
    device = next(model.parameters()).device
    model.eval()
    rows = []
    for cycles in TEST_CYCLES:
        rng = np.random.default_rng([seed, int(cycles * 10)])
        x = np.empty((TEST_PER_POINT, TRACE_LENGTH), dtype=np.float32)
        y = np.empty(TEST_PER_POINT, dtype=np.float32)
        for index in range(TEST_PER_POINT):
            x[index], y[index] = make_example(cycles, rng)
        with torch.no_grad():
            mean, log_variance = model(torch.from_numpy(x).to(device))
        predicted = mean.squeeze(1).cpu().numpy()
        reported_sd = log_variance.squeeze(1).exp().sqrt().cpu().numpy()
        error = np.abs(predicted - y)
        within = error / y <= TOLERANCE
        rows.append({
            "cycles": cycles,
            "accuracy": float(within.mean()),
            "median_abs_error": float(np.median(error)),
            "median_reported_sd": float(np.median(reported_sd)),
            # calibration: actual error against what the model said to expect. Near 1 is
            # honest; far above 1 is confidently wrong.
            "calibration": float(np.median(error / np.maximum(reported_sd, 1e-9))),
        })
    return rows


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    print(f"device: {'cuda' if torch.cuda.is_available() else 'cpu'}, "
          f"{TRAIN_SIZE} training traces, {TEST_PER_POINT} per test point\n")
    output = {"tolerance": TOLERANCE, "conditions": {}}

    for name, (low, high) in CONDITIONS.items():
        print(f"=== {name}  (training cycles {low} to {high})")
        model = train(low, high, ROOT_SEED)
        rows = evaluate(model, ROOT_SEED + 1)
        output["conditions"][name] = rows
        print(f"\n    {'N':>5} {'accuracy':>9} {'|error|':>9} {'reported sd':>12} "
              f"{'calibration':>12}")
        for row in rows:
            flag = "  <- below N_min" if row["cycles"] < 2.5 else ""
            print(f"    {row['cycles']:>5.1f} {row['accuracy']:>8.1%} "
                  f"{row['median_abs_error']:>9.4f} {row['median_reported_sd']:>12.4f} "
                  f"{row['calibration']:>12.2f}{flag}")
        print()

    (RESULTS / "learned_estimator.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    print(f"written: {RESULTS / 'learned_estimator.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
