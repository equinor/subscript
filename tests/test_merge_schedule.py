"""Test the merge_schedule application, which is just another command-line
frontend to sunsch"""
import shutil
import subprocess
from pathlib import Path

import pytest

from subscript.merge_schedule import merge_schedule


# pylint: disable=redefined-outer-name  # conflict with fixtures
# pylint: disable=unused-argument  # conflict with fixtures


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    subprocess.check_output(["merge_schedule", "-h"])


@pytest.fixture
def datadir(tmpdir):
    """A fixture that provides selected input files, copied from sunsch's
    testdata"""
    testdatadir = Path(__file__).absolute().parent / "testdata_sunsch"
    tmpdir.chdir()
    wanted_files = ["mergeme.sch", "initwithdates.sch", "merge2.sch"]
    for filename in wanted_files:
        shutil.copy(testdatadir / filename, filename)
    yield


def test_main(datadir, mocker):
    """Test command line merge_schedule"""

    mocker.patch(
        "sys.argv",
        [
            "merge_schedule",
            "--verbose",
            "mergeme.sch",
            "merge2.sch",
            "merged.sch",
        ],
    )
    merge_schedule.main()

    assert Path("merged.sch").exists()
    assert len(open("merged.sch").readlines()) == 32


def test_initwithdates(datadir, mocker):
    """Test that the first file can contain statements prior to the first
    DATES"""

    mocker.patch(
        "sys.argv",
        [
            "merge_schedule",
            "--verbose",
            "initwithdates.sch",
            "merge2.sch",
            "merged.sch",
        ],
    )
    merge_schedule.main()
    assert Path("merged.sch").exists()
    merged = open("merged.sch").read()
    assert merged.count("\n") == 28
    assert "BAR-FOO" in merged  # This magic string is first in initwithdates
    assert "5 'NOV' 2020" in merged
    assert "YES" in merged  # From last entry in merge2.sch
    assert "NO" in merged  # From last entry in initwithdates
    # Check date order is correct:
    assert merged.find("YES") > merged.find("NO")


def test_dummy_1(datadir, mocker):
    """Test that the first file can contain statements prior to the
    first DATES, and when we don't do any merges (dummy situation)"""
    mocker.patch(
        "sys.argv", ["merge_schedule", "--verbose", "initwithdates.sch", "merged.sch"]
    )
    merge_schedule.main()
    assert len(open("merged.sch").readlines()) == 12


def test_dummy2(datadir, mocker):
    """Another dummy situation"""
    mocker.patch(
        "sys.argv", ["merge_schedule", "--verbose", "merge2.sch", "merged.sch"]
    )
    merge_schedule.main()
    assert len(open("merged.sch").readlines()) == 16


def test_statements_prior_to_dates(datadir, mocker):
    """When we have to files with statements prior to DATES, it is not
    obvious what the users means. Sunsch has chosen to group these to
    a single block that occurs together before the first occurence of any
    DATES in the final output"""
    mocker.patch(
        "sys.argv",
        [
            "merge_schedule",
            "--verbose",
            "merge2.sch",
            "initwithdates.sch",
            "merged.sch",
        ],
    )
    merge_schedule.main()
    merged_str = open("merged.sch").read()
    assert merged_str.find("BAR-FOO") < merged_str.find("DATES")


def test_force(datadir, mocker):
    """Test that --force is working"""
    Path("existing.sch").write_text("bogus")
    mocker.patch(
        "sys.argv", ["merge_schedule", "mergeme.sch", "merge2.sch", "existing.sch"]
    )
    merge_schedule.main()
    assert len(open("existing.sch").readlines()) == 1

    mocker.patch(
        "sys.argv",
        [
            "merge_schedule",
            "mergeme.sch",
            "merge2.sch",
            "existing.sch",
            "--force",
        ],
    )
    merge_schedule.main()
    assert len(open("existing.sch").readlines()) == 32


def test_clip_end(datadir, mocker):
    """Test --clip_end"""
    mocker.patch(
        "sys.argv",
        [
            "merge_schedule",
            "mergeme.sch",
            "merge2.sch",
            "merged.sch",
            "--force",
            "--clip_end",
            "2025-01-01",
        ],
    )
    merge_schedule.main()
    assert len(open("merged.sch").readlines()) == 21
