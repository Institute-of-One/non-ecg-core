"""The cardiac-rate check reports zero. Prove that it would not report zero if a rate were there.

A detector that never fires and a dataset that never carries the rate produce the same
output. This builds synthetic series carrying the rate by each of the two routes the check
knows about, and requires the check to find both. The second route exists because the first
version of this test passed while the script was blind to it: a Siemens cardiac acquisition
leaves HeartRate empty and writes OSCRATEAVG075BPM into ScanOptions instead.

    python -m pytest analysis/test_check_cardiac_tags.py
"""

from __future__ import annotations

import json

from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

import check_cardiac_tags as check


def _write_instance(path, heart_rate=None, scan_options=None):
    ds = Dataset()
    ds.file_meta = FileMetaDataset()
    ds.file_meta.MediaStorageSOPClassUID = CTImageStorage
    ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.SOPClassUID = CTImageStorage
    ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
    ds.Modality = "CT"
    if heart_rate is not None:
        ds.HeartRate = heart_rate
    if scan_options is not None:
        ds.ScanOptions = scan_options
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        ds.save_as(path, enforce_file_format=True)
    except TypeError:                      # pydicom < 3
        ds.is_little_endian = True
        ds.is_implicit_VR = False
        ds.save_as(path, write_like_original=False)


def _run(tmp_path, monkeypatch, series):
    """series: one (heart_rate, scan_options) pair per synthetic series."""
    cache = tmp_path / "data_cache"
    for index, (rate, options) in enumerate(series):
        _write_instance(cache / f"series{index}" / "00000001.dcm", rate, options)
    out = tmp_path / "cardiac_tags.json"
    monkeypatch.setattr(check, "CACHE", cache)
    monkeypatch.setattr(check, "OUT", out)
    check.main()
    return json.loads(out.read_text(encoding="utf-8"))


def test_absent_rate_reports_zero(tmp_path, monkeypatch):
    result = _run(tmp_path, monkeypatch, [(None, None), (None, "HELICAL MODE")])
    assert result["series_checked"] == 2
    assert result["series_with_any_cardiac_field"] == 0


def test_injected_heart_rate_tag_is_found(tmp_path, monkeypatch):
    result = _run(tmp_path, monkeypatch, [(None, None), (72, None), (None, None)])
    assert result["series_with_standard_field"] == 1
    assert result["series_with_any_cardiac_field"] == 1
    assert result["per_tag_present"]["HeartRate"] == 1


def test_rate_hidden_in_scan_options_is_found(tmp_path, monkeypatch):
    """The real Siemens case: HeartRate empty, the rate written as free text."""
    options = ["TP50PC0796", "OSCRATEMIN072BPM", "OSCRATEMAX078BPM", "OSCRATEAVG075BPM",
               "BESTPHASE_OFF"]
    result = _run(tmp_path, monkeypatch, [(None, None), (None, options)])
    assert result["series_with_standard_field"] == 0, "no standard field was written"
    assert result["series_with_rate_in_scan_options"] == 1
    assert result["series_with_any_cardiac_field"] == 1
    carrying = [s for s in result["series"] if s["rates_in_scan_options"]][0]
    assert carrying["rates_in_scan_options"] == {
        "OSCRATEMIN": 72, "OSCRATEMAX": 78, "OSCRATEAVG": 75,
    }


def test_a_silently_unreadable_series_is_not_counted_as_a_negative(tmp_path, monkeypatch):
    """An empty series directory must stop the run, not shrink the denominator."""
    cache = tmp_path / "data_cache"
    _write_instance(cache / "series0" / "00000001.dcm")
    (cache / "series1_empty").mkdir(parents=True)
    monkeypatch.setattr(check, "CACHE", cache)
    monkeypatch.setattr(check, "OUT", tmp_path / "cardiac_tags.json")
    try:
        check.main()
    except SystemExit as exit_:
        assert "a series produced no readable instance" in str(exit_)
    else:                                   # pragma: no cover
        raise AssertionError("an unreadable series was absorbed into the negative result")
