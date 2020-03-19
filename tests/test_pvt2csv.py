"""
Test the pvt2csv module
"""

from __future__ import absolute_import

import sys
import os

import pandas as pd

from subscript.pvt2csv import pvt2csv


def test_pvt2csv(tmpdir):
    """Test the command line utility on a sample input file"""

    assert os.system("pvt2csv -h") == 0

    testdatadir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data/reek/eclipse/include/props"
    )
    pvtfile = os.path.join(testdatadir, "reek.pvt")

    tmpdir.chdir()
    sys.argv = ["pvt2csv", pvtfile]
    pvt2csv.main()
    dframe = pd.read_csv("pvt.csv")

    assert "FILENAME" in dframe
    assert "PVTNUM" in dframe
    assert "OILDENSITY" in dframe
    assert "KEYWORD" in dframe
    assert "PRESSURE" in dframe
    assert "VOLUMEFACTOR" in dframe

    assert not dframe.empty
