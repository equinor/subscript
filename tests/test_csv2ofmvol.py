from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
import os
import pandas as pd
import pytest

from subscript.csv2ofmvol import csv2ofmvol

PRODDATA_A3 = pd.DataFrame(
    data={
        "DATE": ["2010-01-01", "2011-01-01", "2012-01-01"],
        "WELL": ["A-3", "A-3", "A-3"],
        "WOPR": [1000, 2000, 3000],
    }
)


PRODDATA_A4 = pd.DataFrame(
    data={
        "DATE": ["2010-01-01", "2011-01-01", "2012-01-01"],
        "WELL": ["A-4", "A-4", "A-4"],
        "WOPR": [2000, 4000, 5000],
    }
)


def test_read_pdf_csv_files():
    """Test parsing of CSV or dataframes"""
    with pytest.raises(TypeError):
        csv2ofmvol.read_pdm_csv_files()
    with pytest.raises(IOError):
        csv2ofmvol.read_pdm_csv_files(["foobar"])
    with pytest.raises(IOError):
        csv2ofmvol.read_pdm_csv_files("foobar")

    processeddata = csv2ofmvol.read_pdm_csv_files(PRODDATA_A3)
    assert processeddata.index.names[0] == "WELL"
    assert processeddata.index.names[1] == "DATE"
    assert processeddata.columns == ["WOPR"]  # DATE and WELL is index
    assert len(processeddata) == len(PRODDATA_A3)

    processeddata = csv2ofmvol.read_pdm_csv_files([PRODDATA_A3, PRODDATA_A4])
    assert len(processeddata) == len(PRODDATA_A3) + len(PRODDATA_A4)

    with pytest.raises(ValueError):
        csv2ofmvol.read_pdm_csv_files(pd.DataFrame())


def test_cvs2volstr():
    """Test that we can produce strings from dataframes"""
    data = csv2ofmvol.read_pdm_csv_files([PRODDATA_A3, PRODDATA_A4])

    volstr = csv2ofmvol.df2vol(data)
    assert isinstance(volstr, str)
    print(volstr)

    dupdata = csv2ofmvol.read_pdm_csv_files([PRODDATA_A3, PRODDATA_A4, PRODDATA_A3])
    assert len(dupdata) == len(data)


def test_main():
    """Test command line interface"""

    # Test installation
    assert os.system("csv2ofmvol -h") == 0

    curdir = os.path.dirname(__file__)
    testdatadir = os.path.join(curdir, "testdata_csv2ofmvol")
    if not os.path.exists(testdatadir):
        os.mkdir(testdatadir)
    os.chdir(testdatadir)
    PRODDATA_A3.to_csv("prodA3.csv", index=False)
    PRODDATA_A4.to_csv("prodA4.csv", index=False)
    sys.argv = ["csv2ofmvol", "prodA3.csv", "prodA4.csv", "-o", "outfile.vol"]
    csv2ofmvol.main()
    vollines = open("outfile.vol").readlines()
    assert sum(["*NAME" in line for line in vollines]) == 2
    assert sum(["*METRIC" in line for line in vollines]) == 1
    assert sum(["NAME A-3" in line for line in vollines]) == 1
    assert sum(["NAME A-4" in line for line in vollines]) == 1
    assert sum(["*OIL" in line for line in vollines]) == 1
