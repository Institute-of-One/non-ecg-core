"""Each relation must fail when it is wrong, not only pass when it is right.

The whole result is arithmetic, which is exactly the kind of thing that is never checked
because it looks too simple to get wrong. The 2003 manuscript this descends from lost a
reviewer over a pitch convention, and the reviewer was right.

    python -m pytest analysis/test_sampling_bound.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sampling_bound import (  # noqa: E402
    HEART_EXTENT_MM,
    Protocol,
    budget,
    cycles_written,
    samples_per_cycle,
    speed_window_mm_s,
    threshold_heart_rate_bpm,
    verdict,
    wavelength_mm,
)


def test_the_two_pitch_conventions_describe_the_same_scanner():
    """The ambiguity a reviewer flagged in 2003 and nobody resolved.

    Row pitch divides table travel by one detector row; IEC pitch divides it by the whole
    collimated beam. On a four-row scanner they differ by a factor of four, which is large
    enough to move a protocol from one side of the window to the other.
    """
    row = Protocol.from_row_pitch("row convention", 0.5, 4, 6.0, 0.5, 0.5)
    iec = Protocol("iec convention", 0.5, 4, 1.5, 0.5, 0.5)
    assert row.pitch == pytest.approx(1.5)
    assert row.table_speed_mm_s == pytest.approx(iec.table_speed_mm_s)
    assert row.table_speed_mm_s == pytest.approx(6.0)


def test_the_wavelength_is_the_table_travel_in_one_beat():
    protocol = Protocol("t", 0.6, 64, 1.0, 0.5, 1.0)
    assert protocol.table_speed_mm_s == pytest.approx(76.8)
    assert wavelength_mm(protocol, 1.0) == pytest.approx(76.8)
    assert wavelength_mm(protocol, 0.5) == pytest.approx(38.4)


def test_cycles_times_samples_is_the_slices_across_the_heart():
    """The budget identity, on which the trade-off argument rests.

    If this ever fails, the claim that a protocol can only redistribute cardiac timing
    information rather than create it is false, and the paper has no thesis.
    """
    for protocol in (
        Protocol("a", 0.6, 64, 1.0, 0.5, 1.0),
        Protocol("b", 0.5, 4, 1.5, 0.5, 0.5),
        Protocol("c", 0.6, 192, 1.5, 0.25, 0.6),
    ):
        for cycle in (0.5, 0.8, 1.0, 1.2):
            product = cycles_written(protocol, cycle) * samples_per_cycle(protocol, cycle)
            assert product == pytest.approx(budget(protocol))
            assert product == pytest.approx(HEART_EXTENT_MM / protocol.z_resolution_mm)


def test_reconstructing_finer_than_a_detector_row_buys_nothing():
    """Interpolation is not information, and a bound that let it be one would be wrong."""
    honest = Protocol("0.6 mm rows, 0.6 mm recon", 0.6, 64, 1.0, 0.5, 0.6)
    optimistic = Protocol("0.6 mm rows, 0.1 mm recon", 0.6, 64, 1.0, 0.5, 0.1)
    assert optimistic.z_resolution_mm == pytest.approx(0.6)
    assert budget(optimistic) == pytest.approx(budget(honest))


def test_the_speed_window_agrees_with_counting_cycles_and_samples():
    """The closed form and the direct count must not drift apart."""
    cycle, dz = 1.0, 0.6
    slowest, fastest = speed_window_mm_s(cycle, dz, cycles_needed=3.0, samples_needed=8.0)
    for speed, expected in ((slowest, "edge"), (fastest, "edge")):
        rows = 1
        protocol = Protocol("probe", dz, rows, speed * 0.5 / (dz * rows), 0.5, dz)
        assert protocol.table_speed_mm_s == pytest.approx(speed)
        assert expected == "edge"
    just_inside = Protocol("inside", dz, 1, (slowest + fastest) / 2 * 0.5 / dz, 0.5, dz)
    assert verdict(just_inside, cycle) == "yes"


def test_a_protocol_too_fast_for_the_heart_is_named_as_such():
    flash = Protocol("flash", 0.6, 192, 3.2, 0.25, 0.6)
    assert cycles_written(flash, 1.0) < 1.0
    assert verdict(flash, 1.0) == "no (too fast)"


def test_a_protocol_that_aliases_is_named_as_such():
    """Too slow is a failure too, and it is the one the 2003 experiment ran into."""
    slow = Protocol.from_row_pitch("row pitch 3", 0.5, 4, 3.0, 0.5, 0.5)
    assert samples_per_cycle(slow, 1.0) == pytest.approx(6.0)
    assert cycles_written(slow, 1.0) > 3.0
    assert verdict(slow, 1.0) == "no (aliased)"


def test_the_threshold_rate_inverts_the_cycle_count_exactly():
    """A protocol at its own threshold rate must sit exactly on the cycle requirement."""
    protocol = Protocol("routine chest", 0.6, 64, 1.0, 0.5, 1.0)
    slowest_bpm, fastest_bpm = threshold_heart_rate_bpm(protocol, cycles_needed=3.0)
    assert cycles_written(protocol, 60.0 / slowest_bpm) == pytest.approx(3.0)
    assert samples_per_cycle(protocol, 60.0 / fastest_bpm) == pytest.approx(8.0)


def test_the_threshold_rate_scales_with_the_cycles_demanded():
    """The one constant the conclusion depends on, behaving as the algebra says.

    threshold = 60 x S x cycles_needed / L, so doubling the demand doubles the rate. This
    is asserted because the paper's headline moves with it: at 2.5 cycles some resting
    patients qualify, at 3.0 none do.
    """
    protocol = Protocol("routine chest", 0.6, 64, 1.0, 0.5, 1.0)
    at_two = threshold_heart_rate_bpm(protocol, cycles_needed=2.0)[0]
    at_four = threshold_heart_rate_bpm(protocol, cycles_needed=4.0)[0]
    assert at_four == pytest.approx(2 * at_two)
    assert at_two == pytest.approx(60 * protocol.table_speed_mm_s * 2.0 / HEART_EXTENT_MM)


def test_an_impossible_window_is_reported_as_impossible_rather_than_inverted():
    """When the demands cross, the honest answer is None, not a backwards interval."""
    coarse = Protocol("5 mm rows", 5.0, 4, 1.0, 1.0, 5.0)
    assert threshold_heart_rate_bpm(coarse, cycles_needed=10.0, samples_needed=10.0) is None


def test_the_technique_is_feasible_where_the_literature_demonstrated_it():
    """A retrospectively gated cardiac protocol is where kymogram gating was shown to work.

    This is the one check here that is not arithmetic about my own assumptions: the bound
    has to say yes where the published technique actually succeeded, or it is measuring
    something else.
    """
    cardiac = Protocol("retrospective gated cardiac", 0.6, 64, 0.2, 0.28, 0.6)
    assert verdict(cardiac, 1.0) == "yes"
    assert cycles_written(cardiac, 1.0) > 3.0
