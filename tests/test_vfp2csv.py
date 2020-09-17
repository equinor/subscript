import sys
import os

import subprocess
import pytest

import pandas as pd

from subscript.vfp2csv import vfp2csv


def test_vfp2csv(tmpdir):
    """Test the command line utility on sample input files"""
    tmpdir.chdir()

    testdatadir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/vfp")

    vfpfile1 = os.path.join(testdatadir, "pd2.VFP")
    sys.argv = ["vfp2csv", vfpfile1, "-o", "pd2.csv"]
    vfp2csv.main()
    dframe = pd.read_csv("pd2.csv")
    assert "FILENAME" in dframe
    assert "WCT" in dframe
    assert "LIQ" in dframe
    assert "BHP" in dframe
    assert not dframe.empty

    vfpfile2 = os.path.join(testdatadir, "GasProd.VFP")
    sys.argv = ["vfp2csv", vfpfile2, "-o", "gasprod.csv"]
    vfp2csv.main()
    dframe = pd.read_csv("gasprod.csv")
    assert "GAS" in dframe
    assert "BHP" in dframe
    assert "OGR" in dframe
    assert "FILENAME" in dframe


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed"""
    assert subprocess.check_output(["vfp2csv", "-h"])
