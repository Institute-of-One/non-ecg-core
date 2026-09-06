"""When does a helical CT scan record the heartbeat of the heart it is imaging?

A helical scan moves the table at a constant speed, so the z axis of the reconstructed
volume is a time axis with a known scale. A structure that moves periodically writes that
period into the image as a spatial period along z. For the heart this is the wavy cardiac
border seen in a coronal reformat, and it carries the cardiac cycle whether or not an
electrocardiogram was recorded.

Whether the period can be *recovered* from it is a sampling question with two sides, and
they pull against each other:

  * the scan must be slow enough that more than one cycle is written across the heart,
    otherwise there is no period to measure -- only a fragment of one;
  * the scan must be fast enough that each cycle is spread over enough reconstructed
    slices to be resolved, otherwise the waveform aliases.

Both are conditions on one quantity, the table speed, so they define a window. This module
computes that window in closed form, and evaluates where real protocols fall in it.

Everything needed is in the DICOM header of any helical acquisition -- table speed
(0018,9309) or, equivalently, spiral pitch factor (0018,9311) with total collimation
(0018,9307) and revolution time (0018,9305). No image and no patient data is required to
say whether a given scan could carry the signal.

    python analysis/sampling_bound.py
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------- assumptions

#: Craniocaudal extent of the adult heart, in millimetres. The signal is written by the
#: moving cardiac border, so this -- not the scan length -- is the length available to
#: write it on. Varied in the sensitivity analysis rather than assumed exact.
HEART_EXTENT_MM = 120.0

#: Cardiac cycles that must be written across the heart before a period can be said to
#: have been measured. Two is the formal Nyquist floor for a periodic signal; three is
#: what it takes to see that the period repeats rather than to assume it.
CYCLES_NEEDED = 3.0

#: Reconstructed samples per cardiac cycle needed to resolve the waveform. Two is again
#: the formal floor and is not usable: a two-sample sine is a straight line to any
#: estimator with noise in it. Eight is the working value here, and the result is reported
#: against a range because this is the one number in the analysis that is a judgement.
SAMPLES_PER_CYCLE_NEEDED = 8.0


@dataclass(frozen=True)
class Protocol:
    """A helical acquisition, in the terms the DICOM header uses.

    ``pitch`` is the IEC spiral pitch factor (0018,9311): table travel per rotation
    divided by the *total* collimated beam width. This is worth stating, because the
    other convention -- travel per rotation divided by a *single* row width -- was in use
    on four-row scanners and differs by the number of rows. A reviewer of the 2003
    manuscript this work descends from flagged exactly that ambiguity, and it went
    unresolved; ``from_row_pitch`` converts, so the two can never be silently mixed here.
    """

    name: str
    single_collimation_mm: float
    rows: int
    pitch: float
    rotation_time_s: float
    reconstruction_interval_mm: float

    @classmethod
    def from_row_pitch(cls, name, single_collimation_mm, rows, row_pitch, rotation_time_s,
                       reconstruction_interval_mm):
        """Build from the older convention, where pitch divides by one row, not the beam."""
        return cls(name, single_collimation_mm, rows, row_pitch / rows, rotation_time_s,
                   reconstruction_interval_mm)

    @property
    def total_collimation_mm(self) -> float:
        return self.single_collimation_mm * self.rows

    @property
    def table_speed_mm_s(self) -> float:
        """DICOM (0018,9309). The scale factor between the z axis and time."""
        return self.pitch * self.total_collimation_mm / self.rotation_time_s

    @property
    def z_resolution_mm(self) -> float:
        """The finer of the reconstruction interval and the single-row collimation.

        Reconstructing at a smaller interval than one detector row does not create
        information about z; it interpolates. Taking the coarser of the two as the
        sampling step is therefore the honest floor, and it keeps the result free of any
        model of how the slice sensitivity profile broadens with pitch -- which would
        only make the bound tighter, never looser.
        """
        return max(self.reconstruction_interval_mm, self.single_collimation_mm)


def wavelength_mm(protocol: Protocol, cardiac_cycle_s: float) -> float:
    """Table travel during one cardiac cycle: the spatial period written into the volume.

    This is the relation the whole analysis rests on, W = Th x S, with the table speed
    expanded into the parameters the scanner is set by.
    """
    return cardiac_cycle_s * protocol.table_speed_mm_s


def cycles_written(protocol: Protocol, cardiac_cycle_s: float, heart_mm=HEART_EXTENT_MM):
    return heart_mm / wavelength_mm(protocol, cardiac_cycle_s)


def samples_per_cycle(protocol: Protocol, cardiac_cycle_s: float) -> float:
    return wavelength_mm(protocol, cardiac_cycle_s) / protocol.z_resolution_mm


def speed_window_mm_s(cardiac_cycle_s, z_resolution_mm, heart_mm=HEART_EXTENT_MM,
                      cycles_needed=CYCLES_NEEDED,
                      samples_needed=SAMPLES_PER_CYCLE_NEEDED):
    """The table speeds at which the cardiac period is recoverable, as (slowest, fastest).

    Requiring at least ``samples_needed`` slices per cycle puts a floor under the speed;
    requiring at least ``cycles_needed`` cycles across the heart puts a ceiling on it:

        samples_needed x dz / Th  <=  S  <=  L / (Th x cycles_needed)

    The window is empty when the two cross, which happens when dz is coarse relative to
    the heart -- an emptiness that depends on the scanner's z sampling alone and not on
    how it is driven.
    """
    slowest = samples_needed * z_resolution_mm / cardiac_cycle_s
    fastest = heart_mm / (cardiac_cycle_s * cycles_needed)
    return slowest, fastest


def budget(protocol: Protocol, heart_mm=HEART_EXTENT_MM) -> float:
    """Cycles x samples-per-cycle, which is just the slices across the heart.

    The identity N x n = L / dz is trivial once written down and is the point: the total
    information about cardiac timing in the scan is fixed by how finely z is sampled
    across the heart. Pitch, rotation time and heart rate decide only how that fixed
    budget is *divided* between cycles observed and resolution within a cycle. A protocol
    cannot buy more cardiac timing by going faster or slower; it can only trade.
    """
    return heart_mm / protocol.z_resolution_mm


# ------------------------------------------------------------------------ protocols

#: Representative acquisitions. The 2003 rows are the scanner the original observation was
#: made on, in its own pitch convention; the rest are ordinary modern settings.
PROTOCOLS = [
    Protocol.from_row_pitch("2003 4-row, row-pitch 6 (the original)", 0.5, 4, 6.0, 0.5, 0.5),
    Protocol.from_row_pitch("2003 4-row, row-pitch 3 (reported aliased)", 0.5, 4, 3.0, 0.5, 0.5),
    Protocol("2026 routine chest, 64 x 0.6, pitch 1.0", 0.6, 64, 1.0, 0.5, 1.0),
    Protocol("2026 routine chest, thin recon 0.6 mm", 0.6, 64, 1.0, 0.5, 0.6),
    Protocol("2026 lung screening, 64 x 0.6, pitch 1.2", 0.6, 64, 1.2, 0.5, 1.0),
    Protocol("2026 wide detector, 192 x 0.6, pitch 1.5", 0.6, 192, 1.5, 0.25, 0.6),
    Protocol("2026 dual-source high pitch (flash), 3.2", 0.6, 192, 3.2, 0.25, 0.6),
    Protocol("cardiac CT, retrospective gating, pitch 0.2", 0.6, 64, 0.2, 0.28, 0.6),
]


def threshold_heart_rate_bpm(protocol: Protocol, heart_mm=HEART_EXTENT_MM,
                             cycles_needed=CYCLES_NEEDED,
                             samples_needed=SAMPLES_PER_CYCLE_NEEDED):
    """The heart rates at which this protocol does record a recoverable period.

    Reading the window as a condition on the heart rather than on the scanner turns the
    result around, and the turn is the interesting part. A shorter cardiac cycle packs
    more cycles into the same scanned length, so a protocol that is too fast for a resting
    heart is not too fast for every heart:

        cycles   >= cycles_needed   =>  Th <= L / (S x cycles_needed)   =>  a LOWER bound on rate
        samples  >= samples_needed  =>  Th >= samples_needed x dz / S   =>  an UPPER bound on rate

    Returns (slowest_bpm, fastest_bpm), or None where the two cross and no rate works.
    """
    speed = protocol.table_speed_mm_s
    longest_cycle = heart_mm / (speed * cycles_needed)
    shortest_cycle = samples_needed * protocol.z_resolution_mm / speed
    if shortest_cycle > longest_cycle:
        return None
    return 60.0 / longest_cycle, 60.0 / shortest_cycle


def verdict(protocol: Protocol, cardiac_cycle_s: float) -> str:
    cycles = cycles_written(protocol, cardiac_cycle_s)
    samples = samples_per_cycle(protocol, cardiac_cycle_s)
    if cycles < CYCLES_NEEDED and samples < SAMPLES_PER_CYCLE_NEEDED:
        return "no (both)"
    if cycles < CYCLES_NEEDED:
        return "no (too fast)"
    if samples < SAMPLES_PER_CYCLE_NEEDED:
        return "no (aliased)"
    return "yes"


def main() -> int:
    for heart_rate in (60, 90):
        cycle = 60.0 / heart_rate
        slowest, fastest = speed_window_mm_s(cycle, 0.6)
        print(f"\n=== heart rate {heart_rate} bpm  (cardiac cycle {cycle:.2f} s)")
        print(f"    recoverable table speed, at 0.6 mm z sampling: "
              f"{slowest:.1f} to {fastest:.1f} mm/s")
        print(f"\n    {'protocol':44} {'S mm/s':>9} {'W mm':>8} {'cycles':>7} "
              f"{'n/cyc':>7}  verdict")
        for protocol in PROTOCOLS:
            print(f"    {protocol.name:44} {protocol.table_speed_mm_s:9.1f} "
                  f"{wavelength_mm(protocol, cycle):8.1f} "
                  f"{cycles_written(protocol, cycle):7.2f} "
                  f"{samples_per_cycle(protocol, cycle):7.1f}  {verdict(protocol, cycle)}")

    print("\n=== the same window, read as a condition on the heart rather than the scanner")
    print(f"    {'protocol':44} {'recoverable heart rates':>28}")
    for protocol in PROTOCOLS:
        window = threshold_heart_rate_bpm(protocol)
        if window is None:
            described = "none at any rate"
        else:
            slowest, fastest = window
            described = f"{slowest:.0f} to {fastest:.0f} bpm"
        reachable = "" if window is None or window[0] > 220 else "  <- physiologically reachable"
        print(f"    {protocol.name:44} {described:>28}{reachable}")

    print("\n=== how much of this rests on the two constants")
    print("    The threshold heart rate for a protocol is 60 x S x cycles_needed / L, so it")
    print("    is proportional to cycles_needed and does not involve samples_needed at all.")
    print("    That constant is therefore the whole result, and it is the one this analysis")
    print("    cannot supply: it has to be measured against an estimator and noise.\n")
    routine = PROTOCOLS[2]
    print(f"    {'cycles_needed':>14} {'threshold bpm, routine chest':>30}   verdict at rest (60-100 bpm)")
    for needed in (2.0, 2.5, 3.0, 4.0, 5.0):
        window = threshold_heart_rate_bpm(routine, cycles_needed=needed)
        threshold = window[0] if window else float("inf")
        at_rest = "some resting patients qualify" if threshold <= 100 else "no resting patient qualifies"
        print(f"    {needed:>14.1f} {threshold:>30.0f}   {at_rest}")
    print("\n    samples_needed changes only the upper edge, which for every modern protocol")
    print("    sits far above any physiological rate and so decides nothing:")
    for needed in (4.0, 8.0, 16.0):
        window = threshold_heart_rate_bpm(routine, samples_needed=needed)
        print(f"      samples_needed={needed:>4.0f}  ->  upper edge {window[1]:>6.0f} bpm")

    print("\n=== the budget is fixed by z sampling alone")
    for protocol in PROTOCOLS[:1] + PROTOCOLS[2:4] + PROTOCOLS[5:6]:
        print(f"    {protocol.name:44} dz={protocol.z_resolution_mm:4.1f} mm  "
              f"cycles x samples = {budget(protocol):6.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
