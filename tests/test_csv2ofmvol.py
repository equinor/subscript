import sys
import os
import shutil
import subprocess

import pandas as pd
import pytest

from subscript.csv2ofmvol import csv2ofmvol

try:
    # pylint: disable=unused-import
    import ert_shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False


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
    # pylint: disable=no-value-for-parameter
    with pytest.raises(TypeError):
        # pylint: disable=no-value-for-parameter
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


@pytest.mark.parametrize(
    "dframe,  expected_warning",
    [
        (
            pd.DataFrame(
                data={
                    "DATE": ["2010-01-01", "2010-01-03"],
                    "WELL": ["A-4", "A-4"],
                    "WOPR": [1000, 1000],
                }
            ).set_index(["WELL", "DATE"]),
            "not daily-consecutive",
        ),
        (
            pd.DataFrame(
                data={
                    "DATE": ["2010-01-01", "2010-01-03"],
                    "WELL": ["A-4", "A-4"],
                    "WOPR": [1000, 2000],
                }
            ).set_index(["WELL", "DATE"]),
            "Most common timedelta is: 2",
        ),
        (
            pd.DataFrame(
                data={
                    "DATE": ["2010-01-01", "2010-01-03", "2010-01-04"],
                    "WELL": ["A-4", "A-4", "A-4"],
                    "WOPR": [1000, 1000, 2000],
                }
            ).set_index(["WELL", "DATE"]),
            "Uneven date",
        ),
    ],
)
def test_check_consecutive_dates(dframe, expected_warning, caplog):
    """Test that correct warnings are emitted"""
    caplog.clear()
    csv2ofmvol.check_consecutive_dates(dframe)
    assert expected_warning in caplog.text


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


@pytest.fixture
def datadir(tmpdir):
    """Prepare a tmp directory with some example data preloaded"""
    data = os.path.join(os.path.dirname(__file__), "testdata_csv2ofmvol")
    tmpdir.chdir()
    shutil.copytree(data, "data")
    os.chdir("data")
    yield


@pytest.mark.integration
@pytest.mark.skipif(not HAVE_ERT, reason="Requires ERT to be installed")
def test_ert_hook(datadir):
    """Mock an ERT config with CSV2OFMVOL as a FORWARD_MODEL and run it"""
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-argument
    with open("FOO.DATA", "w") as file_h:
        file_h.write("--Empty")
    ert_config = [
        "ECLBASE FOO.DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH .",
        "FORWARD_MODEL CSV2OFMVOL(<CSVFILES>=prod*.csv, <OUTPUT>=proddata.vol)",
    ]

    ert_config_fname = "test.ert"
    with open(ert_config_fname, "w") as file_h:
        file_h.write("\n".join(ert_config))

    subprocess.call(["ert", "test_run", ert_config_fname])

    assert os.path.exists("proddata.vol")
    with open("proddata.vol") as file_h:
        lines = file_h.readlines()
    assert any("A-3" in line for line in lines)
    assert any("A-4" in line for line in lines)
    assert any("2012-01-01" in line for line in lines)
