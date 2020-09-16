import sys
import os

import subprocess
import pytest

import pandas as pd

from subscript.pvt2csv import pvt2csv


def test_pvt2csv(tmpdir):
    """Test the command line utility on a sample input file"""

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


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["pvt2csv", "-h"])
