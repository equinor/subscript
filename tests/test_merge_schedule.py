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
    merged = open("merged.sch").read()
    assert merged.count("\n") == 28
    assert "BAR-FOO" in merged  # This magic string is first in initwithdates
    assert "5 'NOV' 2020" in merged
    assert "YES" in merged  # From last entry in merge2.sch
    assert "NO" in merged  # From last entry in initwithdates
    # Check date order is correct:
    assert merged.find("YES") > merged.find("NO")

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

    # When we have to files with statements prior to DATES, it is not
    # obvious what the users means. Sunsch has chosen to group these to
    # a single block that occurs together before the first occurence of any
    # DATES in the final output
    sys.argv = [
        "merge_schedule",
        "--verbose",
        "merge2.sch",
        "initwithdates.sch",
        "merged.sch",
    ]
    merge_schedule.main()
    merged_str = open("merged.sch").read()
    assert merged_str.find("BAR-FOO") < merged_str.find("DATES")

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
