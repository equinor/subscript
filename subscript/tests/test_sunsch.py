from __future__ import absolute_import

import pytest  # noqa: F401
import os
import sys

from .. import sunsch


def test_main():
    """Test command line sunsch, loading a yaml file"""
    os.chdir(os.path.join(os.path.dirname(__file__), "testdata_sunsch"))

    outfile = "schedule.sch"  # also in config.yml

    if os.path.exists(outfile):
        os.unlink(outfile)
    sys.argv = ["sunsch", "config.yml"]
    sunsch.main()
    assert os.path.exists(outfile)

    schlines = open(outfile).readlines()
    assert len(schlines) > 70

    # Check footemplate.sch was included:
    assert any(['A-90' in x for x in schlines])

    # Sample check for mergeme.sch:
    assert any(['WRFTPLT' in x for x in schlines])

    # Check for foo1.sch, A-1 should occur twice
    assert sum(['A-1' in x for x in schlines]) == 2

    # Check for substitutetest:
    assert any(['400000' in x for x in schlines])

    # Check for randomid:
    assert any(['A-4' in x for x in schlines])
