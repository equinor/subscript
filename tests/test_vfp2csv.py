import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest
from subscript.vfp2csv import vfp2csv


def test_vfp2csv(tmp_path, mocker):
    """Test the command line utility on sample input files"""
    os.chdir(tmp_path)

    testdatadir = Path(__file__).absolute().parent / "data" / "vfp"

    vfpfile1 = testdatadir / "pd2.VFP"
    mocker.patch("sys.argv", ["vfp2csv", str(vfpfile1), "-o", "pd2.csv"])
    vfp2csv.main()
    dframe = pd.read_csv("pd2.csv")
    assert "FILENAME" in dframe
    assert "WCT" in dframe
    assert "LIQ" in dframe
    assert "BHP" in dframe
    assert not dframe.empty

    vfpfile2 = testdatadir / "GasProd.VFP"
    mocker.patch("sys.argv", ["vfp2csv", str(vfpfile2), "-o", "gasprod.csv"])
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
