# How much of a heartbeat a non-gated CT records: a header-computable sampling bound, and what a learned estimator does beyond it

<!-- Every number below is a marker resolved at build time from paper/frozen/manifest.json.
     Nothing is typed by hand. See paper/collect_results.py. -->

## Abstract

**Background.** Deep-learning methods increasingly correct cardiac motion in non-gated chest
CT, and reimbursement for algorithmic analysis of such scans began in 2026. No public chest
CT records the patient's heart rate, so these methods cannot at present be checked against
ground truth by anyone.

**Purpose.** To derive what a non-gated helical acquisition can contain about cardiac
timing, to measure the constant that condition depends on, and to establish what an
estimator does when the acquisition contains nothing.

**Methods.** A helical scan advances the table at a constant speed, so a periodically moving
structure writes its period into the reconstructed volume as a spatial period along z. We
derive the condition under which that period is recoverable, measure the number of cycles
required by simulation over [[results:manifest.json:metrics.sensitivity_cells]] parameter
combinations, evaluate the condition against
[[results:manifest.json:metrics.header_series]] real chest CT series using headers alone,
test it on [[results:manifest.json:metrics.cohort_analysed]] image series under a criterion
frozen in advance, and train an estimator that reports its own uncertainty.

**Results.** [to be resolved]

**Conclusions.** [to be resolved]

---

## 1. Introduction

<!-- The framing decision, made deliberately: the subject of the opening sentence is what a
     scan can contain, not what we tried to measure. The cohort appears in section 5 as
     corroboration that the bound is necessary but not sufficient, never as the claim. -->

## 2. Theory

### 2.1 The z axis of a helical scan is a time axis

### 2.2 The recoverability window

### 2.3 The budget identity

## 3. How many cycles are needed

### 3.1 Simulation design

### 3.2 N_min is set by the problem, not by the estimator

## 4. Where real protocols fall

### 4.1 Half of the public archive cannot be asked

### 4.2 Table speeds and thresholds

## 5. The bound is necessary and not sufficient

### 5.1 A cohort under a frozen criterion

### 5.2 What fails, and what that locates

## 6. What an estimator does past the bound

### 6.1 A model that reports its own uncertainty

### 6.2 Trained inside the bound, confident outside it

### 6.3 Trained across the boundary, it abstains

## 7. Discussion

## 8. Limitations

## 9. Conclusions

## Declarations

## References
