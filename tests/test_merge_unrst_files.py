import subprocess
from pathlib import Path

import numpy as np
import pytest
import resfo

from subscript.merge_unrst_files import merge_unrst_files

UNRST_HIST = (
    Path(__file__).absolute().parent / "testdata_merge_unrst_files" / "HIST.UNRST"
)
UNRST_PRED = (
    Path(__file__).absolute().parent / "testdata_merge_unrst_files" / "PRED.UNRST"
)


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["merge_unrst_files", "-h"])


@pytest.mark.integration
def test_main_default_output(tmp_path, mocker, monkeypatch):
    """Test invocation from command line"""
    monkeypatch.chdir(tmp_path)

    mocker.patch("sys.argv", ["merge_unrst_files", str(UNRST_HIST), str(UNRST_PRED)])
    merge_unrst_files.main()

    assert Path("MERGED.UNRST").exists()


@pytest.mark.integration
def test_main_with_output(tmp_path, mocker, monkeypatch):
    """Test invocation from command line"""
    monkeypatch.chdir(tmp_path)

    mocker.patch(
        "sys.argv",
        [
            "merge_unrst_files",
            str(UNRST_HIST),
            str(UNRST_PRED),
            "--priority",
            "hist",
            "-o",
            "MY_MERGED.UNRST",
        ],
    )
    merge_unrst_files.main()

    assert Path("MY_MERGED.UNRST").exists()


def get_restart_report_numbers(unrst_merged):
    """Get restart report numbers from merged unrst file."""
    report_numbers = []
    for kw, val in unrst_merged:
        if kw == "SEQNUM  ":
            report_numbers.append(val[0])
    return report_numbers


@pytest.mark.integration
def test_check_report_numbers(tmp_path, mocker, monkeypatch):
    """Verify that merged restart has the expected restart report numbers."""
    monkeypatch.chdir(tmp_path)

    mocker.patch(
        "sys.argv",
        [
            "merge_unrst_files",
            str(UNRST_HIST),
            str(UNRST_PRED),
            "--priority",
            "hist",
            "-o",
            "MY_MERGED.UNRST",
        ],
    )
    merge_unrst_files.main()

    expected_report_numbers = [0, 82, 124]
    report_numbers = get_restart_report_numbers(resfo.read("MY_MERGED.UNRST"))

    assert report_numbers == expected_report_numbers


def test_split_by_seqnum():
    """Test splitting into chunks."""

    data = [
        ("SEQNUM  ", np.array([1])),
        ("PRESSURE", np.array([1.0])),
        ("SEQNUM  ", np.array([2])),
        ("PRESSURE", np.array([2.0])),
    ]

    chunks = merge_unrst_files._split_by_seqnum(data)
    assert len(chunks) == 2
    assert merge_unrst_files._get_seqnum(chunks[0]) == 1
    assert merge_unrst_files._get_seqnum(chunks[1]) == 2


def test_is_in_interval():
    """Test interval membership check."""
    assert merge_unrst_files._is_in_interval(5, (3, 7)) is True
    assert merge_unrst_files._is_in_interval(3, (3, 7)) is True
    assert merge_unrst_files._is_in_interval(7, (3, 7)) is True
    assert merge_unrst_files._is_in_interval(2, (3, 7)) is False
    assert merge_unrst_files._is_in_interval(8, (3, 7)) is False
    assert merge_unrst_files._is_in_interval(None, (3, 7)) is False
    assert merge_unrst_files._is_in_interval(5, None) is False


def test_get_overlap_interval():
    """Test overlap detection logic."""

    hist_data = [
        ("SEQNUM  ", np.array([1])),
        ("PRESSURE", np.array([1.0])),
        ("SEQNUM  ", np.array([2])),
        ("PRESSURE", np.array([2.0])),
        ("SEQNUM  ", np.array([3])),
        ("PRESSURE", np.array([3.0])),
    ]
    pred_data = [
        ("SEQNUM  ", np.array([2])),
        ("PRESSURE", np.array([2.5])),
        ("SEQNUM  ", np.array([3])),
        ("PRESSURE", np.array([3.5])),
        ("SEQNUM  ", np.array([4])),
        ("PRESSURE", np.array([4.0])),
    ]

    hist_chunks = merge_unrst_files._split_by_seqnum(hist_data)
    pred_chunks = merge_unrst_files._split_by_seqnum(pred_data)

    interval = merge_unrst_files._get_overlap_interval(hist_chunks, pred_chunks)
    assert interval == (2, 3)


def test_get_overlap_interval_no_overlap():
    """Test when there is no overlap."""

    hist_data = [
        ("SEQNUM  ", np.array([1])),
        ("SEQNUM  ", np.array([2])),
    ]
    pred_data = [
        ("SEQNUM  ", np.array([3])),
        ("SEQNUM  ", np.array([4])),
    ]

    hist_chunks = merge_unrst_files._split_by_seqnum(hist_data)
    pred_chunks = merge_unrst_files._split_by_seqnum(pred_data)

    interval = merge_unrst_files._get_overlap_interval(hist_chunks, pred_chunks)
    assert interval is None


@pytest.fixture
def overlapping_unrst_files(tmp_path):
    """Create overlapping UNRST files for testing."""

    hist_data = [
        ("SEQNUM  ", np.array([1], dtype=np.int32)),
        ("PRESSURE", np.array([100.0])),
        ("SEQNUM  ", np.array([2], dtype=np.int32)),
        ("PRESSURE", np.array([200.0])),
        ("SEQNUM  ", np.array([3], dtype=np.int32)),
        ("PRESSURE", np.array([300.0])),
    ]
    pred_data = [
        ("SEQNUM  ", np.array([2], dtype=np.int32)),
        ("PRESSURE", np.array([250.0])),
        ("SEQNUM  ", np.array([3], dtype=np.int32)),
        ("PRESSURE", np.array([350.0])),
        ("SEQNUM  ", np.array([4], dtype=np.int32)),
        ("PRESSURE", np.array([400.0])),
    ]

    hist_path = tmp_path / "HIST.UNRST"
    pred_path = tmp_path / "PRED.UNRST"
    resfo.write(str(hist_path), hist_data)
    resfo.write(str(pred_path), pred_data)
    return hist_path, pred_path


def test_priority_hist_with_overlap(overlapping_unrst_files, mocker, monkeypatch):
    """Test --priority hist with overlapping data."""
    hist_path, pred_path = overlapping_unrst_files
    monkeypatch.chdir(hist_path.parent)

    mocker.patch(
        "sys.argv",
        [
            "merge_unrst_files",
            str(hist_path),
            str(pred_path),
            "--priority",
            "hist",
            "-o",
            "MERGED.UNRST",
        ],
    )
    merge_unrst_files.main()

    merged = resfo.read("MERGED.UNRST")

    report_numbers = get_restart_report_numbers(merged)
    # Hist keeps [1,2,3], pred stripped of [2,3], keeps [4]
    assert report_numbers == [1, 2, 3, 4]

    pressures = [val[0] for kw, val in merged if kw == "PRESSURE"]
    # Hist values [100, 200, 300] kept, pred only contributes [400]
    assert pressures == [100.0, 200.0, 300.0, 400.0]


def test_priority_pred_with_overlap(overlapping_unrst_files, mocker, monkeypatch):
    """Test --priority pred with overlapping data."""
    hist_path, pred_path = overlapping_unrst_files
    monkeypatch.chdir(hist_path.parent)

    mocker.patch(
        "sys.argv",
        [
            "merge_unrst_files",
            str(hist_path),
            str(pred_path),
            "--priority",
            "pred",
            "-o",
            "MERGED.UNRST",
        ],
    )
    merge_unrst_files.main()

    merged = resfo.read("MERGED.UNRST")

    report_numbers = get_restart_report_numbers(merged)
    # Hist stripped of [2,3], keeps [1]; pred keeps [2,3,4]
    assert report_numbers == [1, 2, 3, 4]

    pressures = [val[0] for kw, val in merged if kw == "PRESSURE"]
    # Hist keeps [100], pred values [250, 350, 400] kept
    assert pressures == [100.0, 250.0, 350.0, 400.0]


@pytest.mark.integration
def test_ert_integration(tmp_path, monkeypatch):
    pytest.importorskip("ert")
    monkeypatch.chdir(tmp_path)
    ert_config = "config.ert"
    Path(ert_config).write_text(
        f"""
        NUM_REALIZATIONS 1
        RUNPATH .
        FORWARD_MODEL MERGE_UNRST_FILES(<UNRST1>={UNRST_HIST}, \
            <UNRST2>={UNRST_PRED}, <OUTPUT>=MERGED.UNRST)
    """,
        encoding="utf-8",
    )

    result = subprocess.run(
        ["ert", "test_run", "--disable-monitor", ert_config],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"ERT failed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    assert Path("MERGED.UNRST").exists()
