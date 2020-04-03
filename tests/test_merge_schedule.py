"""Test merge_schedule"""
from __future__ import absolute_import


import os
import sys
import subprocess

import pytest

from subscript.merge_schedule import merge_schedule


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    subprocess.check_output(["merge_schedule", "-h"])


def test_main():
    """Test command line merge_schedule"""

    os.chdir(os.path.join(os.path.dirname(__file__), "testdata_sunsch"))

    # Basic test merging two files:
    if os.path.exists("merged.sch"):
        os.unlink("merged.sch")
    sys.argv = [
        "merge_schedule",
        "--verbose",
        "mergeme.sch",
        "merge2.sch",
        "merged.sch",
    ]
    merge_schedule.main()

    assert os.path.exists("merged.sch")
    assert len(open("merged.sch").readlines()) == 32

    # Test that the first file can contain statements prior to the
    # first DATES
    if os.path.exists("merged.sch"):
        os.unlink("merged.sch")
    sys.argv = [
        "merge_schedule",
        "--verbose",
        "initwithdates.sch",
        "merge2.sch",
        "merged.sch",
    ]
    merge_schedule.main()
    assert os.path.exists("merged.sch")
    merged = open("merged.sch").readlines()
    assert len(merged) == 28
    assert "BAR-FOO" in "".join(merged)  # This magic string is first in initwithdates
    assert "5 'NOV' 2020" in "".join(merged)

    # Test that the first file can contain statements prior to the
    # first DATES, and when we don't do any merges (dummy situation)
    if os.path.exists("merged.sch"):
        os.unlink("merged.sch")
    sys.argv = ["merge_schedule", "--verbose", "initwithdates.sch", "merged.sch"]
    merge_schedule.main()
    assert len(open("merged.sch").readlines()) == 12

    # And another dummy situation:
    if os.path.exists("merged.sch"):
        os.unlink("merged.sch")
    sys.argv = ["merge_schedule", "--verbose", "merge2.sch", "merged.sch"]
    merge_schedule.main()
    assert len(open("merged.sch").readlines()) == 16

    # But if we have statements prior to DATES in other files
    # than the first, we want to fail:
    with pytest.raises(ValueError):
        sys.argv = [
            "merge_schedule",
            "--verbose",
            "merge2.sch",
            "initwithdates.sch",
            "merged.sch",
        ]
        merge_schedule.main()

    # Test that --force is working
    with open("existing.sch", "w") as fhandle:
        fhandle.write("bogus")
    sys.argv = ["merge_schedule", "mergeme.sch", "merge2.sch", "existing.sch"]
    merge_schedule.main()
    assert len(open("existing.sch").readlines()) == 1
    sys.argv = [
        "merge_schedule",
        "mergeme.sch",
        "merge2.sch",
        "existing.sch",
        "--force",
    ]
    merge_schedule.main()
    assert len(open("existing.sch").readlines()) == 32

    # Test --clip_end:
    sys.argv = [
        "merge_schedule",
        "mergeme.sch",
        "merge2.sch",
        "merged.sch",
        "--force",
        "--clip_end",
        "2025-01-01",
    ]
    merge_schedule.main()
    assert len(open("merged.sch").readlines()) == 21
