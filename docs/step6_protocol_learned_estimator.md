# Step 6 protocol — does a learned estimator know when it cannot know?

Frozen 2026-09-06, before any model was written or trained.

## Why this exists

The cohort showed that one hand-built estimator recovers a period in 3 of 17 real series.
The obvious objection is that a better estimator would do better, and against that objection
the cohort has no answer.

**A bound does not have that weakness.** Where fewer than `N_min` cycles were written, the
information is absent, and absence constrains every method equally — learned or not. So the
question that survives the objection is not "can a model do better?" but:

> **When the scan did not record the period, does a model say so?**

If it does, the bound is a useful precondition and models can be trusted to respect it. If
it does not — if it emits a confident, wrong period that looks exactly like a correct one —
then the bound is a **safety** result, and a header-computable one, in a field where CMS
began reimbursing algorithmic chest-CT analysis in April 2026.

Either answer is worth having. Both are written down here before either is seen.

## The model

A small network predicting, from a border trace, both a period **and its own uncertainty**,
trained with a Gaussian negative-log-likelihood loss. Predicting uncertainty is not a
courtesy: it is what makes abstention *possible*, so a model that still will not abstain has
no excuse left.

Traces come from the step-3 simulator, which is the only place ground truth exists. Input is
the detrended trace resampled to a fixed length, so the model sees what the hand-built
estimator saw and nothing more.

## Two training conditions, because they ask different questions

- **(a) Trained only where recovery is possible** (`N` >= 2.5). Tested below. This is an
  out-of-distribution test and the expected answer is confident nonsense.
- **(b) Trained across the boundary** (`N` from 0.5 to 8). Tested below. **This is the fair
  test.** The model has seen unrecoverable traces and their true periods during training;
  the question is whether it learns that they are unrecoverable and widens its predicted
  uncertainty, or learns to guess.

Condition (b) is the one that matters, and it is the one a critic would demand.

## Measurements

For each condition, across `N` from 0.5 to 8:

- **accuracy** — fraction of predictions within 5 per cent of the true period, the same
  criterion as step 3;
- **reported uncertainty** — the model's own predicted standard deviation;
- **calibration** — the ratio of actual error to reported uncertainty. A calibrated model
  keeps this near 1 everywhere. A model that is confidently wrong drives it far above 1
  below the bound.

## What each outcome would mean, decided now

- **(b) abstains: reported uncertainty rises sharply below `N_min` and calibration holds.**
  A learned estimator can be taught the bound. This is a **constructive** result and the
  better one for the field: it says how to build a model that refuses honestly, and the
  bound becomes a training target rather than a warning. The paper reports it as such.
- **(b) does not abstain: accuracy collapses below `N_min` while reported uncertainty stays
  flat.** A model trained across the boundary still cannot tell recovery from invention, and
  its output carries no signal that it has crossed into invention. The bound becomes a
  precondition that must be checked outside the model, from the header, before its output is
  believed.
- **(a) and (b) behave alike.** Whatever the direction, the training distribution did not
  matter, which is itself informative about where the limit sits.

The second outcome is the one that would make the strongest paper, which is exactly why it
is written down in advance alongside the first. **The first outcome is better for the world
and worse for the paper, and it will be reported the same way if it happens.**

## What is not claimed

This is a simulation. It says what a model does on traces from the step-3 generator, not
what any published motion-correction system does on real scans. No claim is made about any
named method. The transferable statement is about information, not about anyone's model:
where the acquisition wrote nothing, no estimator recovers anything, and the only question
is whether it admits it.
