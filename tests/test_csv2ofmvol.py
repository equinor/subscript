import sys
import os
import re
import subprocess
import datetime

import pandas as pd
import numpy as np
import pytest

from subscript.csv2ofmvol import csv2ofmvol
from subscript.ofmvol2csv import ofmvol2csv

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
                    "DATE": [],
                    "WELL": [],
                    "WOPR": [],
                }
            ).set_index(["WELL", "DATE"]),
            "",
        ),
        (
            pd.DataFrame(
                data={
                    "DATE": ["2010-01-01"],
                    "WELL": ["A-4"],
                    "WOPR": [1000],
                }
            ).set_index(["WELL", "DATE"]),
            "",
        ),
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


@pytest.mark.parametrize(
    "dframe, expected_lines",
    [
        (
            pd.DataFrame(
                data={
                    "DATE": [datetime.date(2010, 1, 1)],
                    "WELL": ["A-4"],
                    "WOPR": [1000],
                }
            ).set_index(["WELL", "DATE"]),
            ["*METRIC", "*DAILY", "*DATE *OIL", "*NAME A-4", "2010-01-01 1000"],
        ),
        (
            pd.DataFrame(
                data={
                    "DATE": [datetime.date(2010, 1, 1)],
                    "WELL": ["A-4"],
                    "WOPR": [1000],
                    "BOGUS": [88888],
                }
            ).set_index(["WELL", "DATE"]),
            ["*METRIC", "*DAILY", "*DATE *OIL", "*NAME A-4", "2010-01-01 1000"],
        ),
        (
            pd.DataFrame(
                data={
                    "DATE": ["2010-01-01"],
                    "WELL": ["A-4"],
                    "WOPR": [1000],
                    "DAYS": [24.0],
                }
            ).set_index(["WELL", "DATE"]),
            [
                "*METRIC",
                "*DAILY",
                "*HRS_IN_DAYS",
                "*DATE *OIL *DAYS",
                "*NAME A-4",
                "2010-01-01 1000 24.0",
            ],
        ),
        (
            pd.DataFrame(
                data={
                    "DATE": ["2010-01-01"],
                    "WELL": ["A-4"],
                    "GINJ": [100000],
                    "GIDAY": [23.0],
                }
            ).set_index(["WELL", "DATE"]),
            [
                "*METRIC",
                "*DAILY",
                "*HRS_IN_DAYS",
                "*DATE *GINJ *GIDAY",
                "*NAME A-4",
                "2010-01-01 100000 23.0",
            ],
        ),
        (
            pd.DataFrame(
                data={
                    "DATE": ["2010-01-01"],
                    "WELL": ["A-4"],
                    "WINJ": [100000],
                    "WIDAY": [23.0],
                }
            ).set_index(["WELL", "DATE"]),
            [
                "*METRIC",
                "*DAILY",
                "*HRS_IN_DAYS",
                "*DATE *WINJ *WIDAY",
                "*NAME A-4",
                "2010-01-01 100000 23.0",
            ],
        ),
        (
            # Two wells:
            pd.DataFrame(
                data={
                    "DATE": [datetime.date(2010, 1, 1), datetime.date(2010, 1, 1)],
                    "WELL": ["A-4", "A-5"],
                    "WOPR": [1000, 2000],
                }
            ).set_index(["WELL", "DATE"]),
            [
                "*METRIC",
                "*DAILY",
                "*DATE *OIL",
                "*NAME A-4",
                "2010-01-01 1000",
                "*NAME A-5",
                "2010-01-01 2000",
            ],
        ),
        (
            # Test mixing prod and inj, with empty cells.
            pd.DataFrame(
                data={
                    "DATE": ["2010-01-01", "2010-01-02"],
                    "WELL": ["A-4", "A-4"],
                    "WINJ": [1000, np.nan],
                    "GINJ": [np.nan, 1000000],
                }
            ).set_index(["WELL", "DATE"]),
            [
                "*METRIC",
                "*DAILY",
                "*DATE *WINJ *GINJ",
                "*NAME A-4",
                "2010-01-01 1000.0 0.0",
                "2010-01-02 0.0 1000000.0",
            ],
        ),
        (
            # Empty input. This would be an error if it wasn't for the header.
            pd.DataFrame(
                data={
                    "DATE": [],
                    "WELL": [],
                    "OIL": [],
                }
            ).set_index(["WELL", "DATE"]),
            [
                "*METRIC",
                "*DAILY",  # (this is meaningless, and can be dropped)
                "*DATE *OIL",
            ],
        ),
    ],
)
def test_df2vol(dframe, expected_lines):
    """Direct test of the dataframe to vol conversion, including a bonus test
    using ofmvol2csv to see that we can go back again and obtain the same
    dataframe."""
    volstr = csv2ofmvol.df2vol(dframe)
    assert isinstance(volstr, str)
    assert volstr

    # Compare strings, but ignore whitespace differences.
    assert [re.sub(r"\s+", " ", line) for line in volstr.split("\n") if line] == [
        re.sub(r"\s+", " ", line) for line in expected_lines
    ]

    # Bonus test, convert back to dataframe with ofmvol2str:

    # Ensure dates in the multiindes are datetime types, needed for comparison.
    if not dframe.empty:
        dframe.index = dframe.index.set_levels(
            [dframe.index.levels[0], pd.to_datetime(dframe.index.levels[1])]
        )

    # Need to convert column names also as in ofmvol2csv for comparison:
    dframe = dframe.rename(columns=csv2ofmvol.PDMCOLS2VOL)

    backagain_df = ofmvol2csv.process_volstr(volstr)

    if dframe.empty:
        assert backagain_df.empty
    else:
        # (bogus columns in dframe must be ignored)
        pd.testing.assert_frame_equal(
            dframe[backagain_df.columns].fillna(value=0.0), backagain_df
        )


@pytest.mark.parametrize(
    "dframe, expected_error",
    [
        (
            # Empty input
            pd.DataFrame(),
            ValueError,
        ),
        (
            # Not-indexed:
            pd.DataFrame(
                data={
                    "DATE": [],
                    "WELL": [],
                }
            ),
            ValueError,
        ),
        (
            # No supported columns:
            pd.DataFrame(
                data={
                    "DATE": [],
                    "WELL": [],
                }
            ).set_index(["WELL", "DATE"]),
            ValueError,
        ),
        (
            # No supported columns:
            pd.DataFrame(
                data={
                    "DATE": [datetime.date(2020, 1, 1)],
                    "WELL": ["A-1"],
                }
            ).set_index(["WELL", "DATE"]),
            ValueError,
        ),
        (
            # No supported columns:
            pd.DataFrame(
                data={
                    "DATE": [],
                    "WELL": [],
                    "SOAP": [],
                }
            ).set_index(["WELL", "DATE"]),
            ValueError,
        ),
        (
            # No supported columns:
            pd.DataFrame(
                data={
                    "DATE": [datetime.date(2020, 1, 1)],
                    "WELL": ["A-1"],
                    "SOAP": [100],
                }
            ).set_index(["WELL", "DATE"]),
            ValueError,
        ),
    ],
)
def test_df2vol_errors(dframe, expected_error):
    """Test that correct exceptions are raised"""
    with pytest.raises(expected_error):
        csv2ofmvol.df2vol(dframe)


def test_cvs2volstr():
    """Test that we can produce strings from dataframes"""
    data = csv2ofmvol.read_pdm_csv_files([PRODDATA_A3, PRODDATA_A4])

    volstr = csv2ofmvol.df2vol(data)
    assert isinstance(volstr, str)

    dupdata = csv2ofmvol.read_pdm_csv_files([PRODDATA_A3, PRODDATA_A4, PRODDATA_A3])
    assert len(dupdata) == len(data)


def test_main(datadir):
    """Test command line interface"""
    # Test installation
    assert os.system("csv2ofmvol -h") == 0

    sys.argv = ["csv2ofmvol", "prodA3.csv", "prodA4.csv", "-o", "outfile.vol"]
    csv2ofmvol.main()
    vollines = open("outfile.vol").readlines()
    assert sum(["*NAME" in line for line in vollines]) == 2
    assert sum(["*METRIC" in line for line in vollines]) == 1
    assert sum(["NAME A-3" in line for line in vollines]) == 1
    assert sum(["NAME A-4" in line for line in vollines]) == 1
    assert sum(["*OIL" in line for line in vollines]) == 1


def test_emptyfile(tmpdir):
    """Verify behaviour on empty input"""
    tmpdir.chdir()
    # All empty file.
    with open("empty.csv", "w") as file_h:
        file_h.write("")
    with pytest.raises(pd.errors.EmptyDataError):
        csv2ofmvol.csv2ofmvol_main("empty.csv", "empty.vol")
    assert not os.path.exists("empty.vol")

    # CSV file with wrong columns:
    with open("columns.csv", "w") as file_h:
        file_h.write("FOO")
    with pytest.raises(ValueError, match="WELL not found in dataset"):
        csv2ofmvol.csv2ofmvol_main("columns.csv", "columns.vol")
    assert not os.path.exists("columns.vol")

    # CSV file with index columns:
    with open("indexcols.csv", "w") as file_h:
        file_h.write("DATE,WELL")
    with pytest.raises(ValueError, match="No supported data columns provided"):
        csv2ofmvol.csv2ofmvol_main("indexcols.csv", "columns.vol")

    # CSV file with index columns and one data column
    with open("oilcol.csv", "w") as file_h:
        file_h.write("DATE,WELL,OIL")
    csv2ofmvol.csv2ofmvol_main("oilcol.csv", "oilcol.vol")
    lines = open("oilcol.vol").readlines()
    assert len(lines) == 6  # comments + three header lines (metric, daily, date+oil)


@pytest.fixture
def datadir(tmpdir):
    """Prepare a tmp directory with some example data preloaded"""
    tmpdir.chdir()
    PRODDATA_A3.to_csv("prodA3.csv", index=False)
    PRODDATA_A4.to_csv("prodA4.csv", index=False)
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

    subprocess.run(["ert", "test_run", ert_config_fname], check=True)

    assert os.path.exists("proddata.vol")
    with open("proddata.vol") as file_h:
        lines = file_h.readlines()
    assert any("A-3" in line for line in lines)
    assert any("A-4" in line for line in lines)
    assert any("2012-01-01" in line for line in lines)
