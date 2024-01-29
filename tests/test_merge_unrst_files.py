import os
import subprocess
from pathlib import Path

import pytest
import resfo
from subscript.merge_unrst_files import merge_unrst_files

UNRST_HIST = (
    Path(__file__).absolute().parent / "testdata_merge_unrst_files" / "HIST.UNRST"
)
UNRST_PRED = (
    Path(__file__).absolute().parent / "testdata_merge_unrst_files" / "PRED.UNRST"
)

# pylint: disable=protected-access


@pytest.mark.integration
def test_integration():
    """Test that endpoint is installed"""
    assert subprocess.check_output(["merge_unrst_files", "-h"])


@pytest.mark.integration
def test_main_default_output(tmp_path, mocker):
    """Test invocation from command line"""
    os.chdir(tmp_path)

    mocker.patch("sys.argv", ["merge_unrst_files", str(UNRST_HIST), str(UNRST_PRED)])
    merge_unrst_files.main()

    assert Path("MERGED.UNRST").exists()


@pytest.mark.integration
def test_main_with_output(tmp_path, mocker):
    """Test invocation from command line"""
    os.chdir(tmp_path)

    mocker.patch(
        "sys.argv",
        [
            "merge_unrst_files",
            str(UNRST_HIST),
            str(UNRST_PRED),
            "-o",
            "MY_MERGED.UNRST",
        ],
    )
    merge_unrst_files.main()

    assert Path("MY_MERGED.UNRST").exists()


def get_restart_report_numbers(unrst_merged):
    """Get restart report numbers from merged unrst file. It should be [0, 82, 206]"""
    report_numbers = []
    for kw, val in unrst_merged:
        if kw == "SEQNUM  ":
            report_numbers.append(val[0])
    return report_numbers


@pytest.mark.integration
def test_check_report_numbers(tmp_path, mocker):
    """Verify that merged restart has the expected restart report numbers."""
    os.chdir(tmp_path)

    mocker.patch(
        "sys.argv",
        [
            "merge_unrst_files",
            str(UNRST_HIST),
            str(UNRST_PRED),
            "-o",
            "MY_MERGED.UNRST",
        ],
    )
    merge_unrst_files.main()

    expected_report_numbers = [0, 82, 206]
    report_numbers = get_restart_report_numbers(resfo.read("MY_MERGED.UNRST"))

    print(
        f"expected restart report numbers: {expected_report_numbers}, "
        + f"actual restart report_numbers: {report_numbers}"
    )
    assert report_numbers == expected_report_numbers
