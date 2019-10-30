from __future__ import absolute_import


import os
import sys

import pytest  # noqa: F401

from subscript.merge_schedule import merge_schedule


def test_main():
    """Test command line merge_schedule"""
    os.chdir(os.path.join(os.path.dirname(__file__), "testdata_sunsch"))

    # Basic test merging two files:
    if os.path.exists("merged.sch"):
        os.unlink("merged.sch")
    sys.argv = ["merge_schedule", "mergeme.sch", "merge2.sch", "merged.sch"]
    merge_schedule.main()

    assert os.path.exists("merged.sch")
    assert len(open("merged.sch").readlines()) == 32

    # Test that --force is working
    with open("existing.sch", "w") as fh:
        fh.write("bogus")
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
    assert len(open("merged.sch").readlines()) == 32

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
